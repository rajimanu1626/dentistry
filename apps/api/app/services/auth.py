"""Authentication service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.identity import IdentityProvider
from app.core.config import Settings, SignupMode
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    GoneError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.security import (
    constant_time_equals,
    hash_password,
    hmac_sha256,
    random_token,
    verify_password,
)
from app.models import Clinic, ClinicInvite, ClinicMember, ClinicRole, User
from app.schemas.auth import (
    AuthConfigPublic,
    InviteCreated,
    InviteCreateRequest,
    InvitePublic,
)
from app.services import visits as visits_service


class _LocalCredStore:
    """Local credentials store for the ``local`` identity provider.

    Credentials are persisted to a dev-only JSON file so API reloads/restarts
    do not invalidate all local passwords.
    """

    def __init__(self) -> None:
        self._by_email: dict[str, tuple[UUID, str]] = {}
        self._path = Path(__file__).resolve().parents[2] / ".local_credentials.json"
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            payload = json.loads(self._path.read_text())
        except Exception:
            return
        for email, raw in payload.items():
            if not isinstance(raw, dict):
                continue
            uid = raw.get("user_id")
            hashed = raw.get("password_hash")
            if not isinstance(uid, str) or not isinstance(hashed, str):
                continue
            try:
                self._by_email[email.lower()] = (UUID(uid), hashed)
            except ValueError:
                continue

    def _save(self) -> None:
        payload = {
            email: {"user_id": str(user_id), "password_hash": hashed}
            for email, (user_id, hashed) in self._by_email.items()
        }
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload))
        tmp.replace(self._path)

    def set(self, email: str, user_id: UUID, password: str) -> None:
        self._by_email[email.lower()] = (user_id, hash_password(password))
        self._save()

    def set_hashed(self, email: str, user_id: UUID, password_hash: str) -> None:
        self._by_email[email.lower()] = (user_id, password_hash)
        self._save()

    def verify(self, email: str, password: str) -> UUID | None:
        # Reload so CLI-created accounts work without restarting uvicorn.
        self._load()
        rec = self._by_email.get(email.lower())
        if rec is None:
            return None
        user_id, hashed = rec
        if not verify_password(password, hashed):
            return None
        return user_id


_LOCAL_CREDS = _LocalCredStore()


@dataclass(frozen=True, slots=True)
class SignupPolicy:
    mode: SignupMode
    user_count: int

    @property
    def is_empty_db(self) -> bool:
        return self.user_count == 0

    @property
    def can_bootstrap_clinic(self) -> bool:
        if self.mode == "open":
            return True
        if self.mode == "bootstrap":
            return self.is_empty_db
        if self.mode == "invite":
            return self.is_empty_db
        return False

    @property
    def requires_invite(self) -> bool:
        return self.mode == "invite" and not self.is_empty_db

    @property
    def can_signup(self) -> bool:
        if self.mode == "closed":
            return self.can_bootstrap_clinic
        if self.mode == "open":
            return True
        if self.mode == "bootstrap":
            return self.is_empty_db
        # invite
        return True

    def to_public(self) -> AuthConfigPublic:
        return AuthConfigPublic(
            signup_mode=self.mode,
            can_signup=self.can_signup,
            can_bootstrap_clinic=self.can_bootstrap_clinic,
            requires_invite=self.requires_invite,
        )


async def count_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(User))
    return int(result.scalar_one())


async def get_signup_policy(session: AsyncSession, settings: Settings) -> SignupPolicy:
    async with session.begin():
        await session.execute(text("SET LOCAL row_security = off;"))
        total = await count_users(session)
    return SignupPolicy(mode=settings.signup_mode, user_count=total)


def _ensure_local_identity(settings: Settings) -> None:
    if settings.identity_provider != "local":
        raise UnauthorizedError(
            "Login flows for non-local identity providers go through the IdP, not this endpoint."
        )


async def _resolve_invite_by_token(
    session: AsyncSession,
    *,
    raw_token: str,
    settings: Settings,
) -> ClinicInvite:
    if not raw_token or len(raw_token) > 256:
        raise NotFoundError("Invalid invite token.")
    expected = hmac_sha256(settings.invite_hmac_secret_value, raw_token)
    result = await session.execute(select(ClinicInvite).where(ClinicInvite.token_hmac == expected))
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError("Invite not found.")
    if not constant_time_equals(bytes(row.token_hmac), expected):
        raise NotFoundError("Invite not found.")
    return row


def _validate_invite_row(invite: ClinicInvite, *, email: str) -> None:
    if invite.revoked_at is not None:
        raise GoneError("This invite has been revoked.")
    if invite.accepted_at is not None:
        raise GoneError("This invite has already been used.")
    if invite.expires_at <= datetime.now(UTC):
        raise GoneError("This invite has expired.")
    if invite.email.lower() != email.lower():
        raise ForbiddenError("This invite was issued for a different email address.")


async def signup(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    clinic_name: str | None,
    clinic_slug: str | None,
    invite_token: str | None,
    settings: Settings,
    identity: IdentityProvider,
) -> tuple[User, Clinic | None, str]:
    """Register a user (bootstrap new clinic or accept a clinic invite)."""
    _ensure_local_identity(settings)

    policy = await get_signup_policy(session, settings)
    if not policy.can_signup:
        raise ForbiddenError("Sign-up is disabled on this instance.")

    if invite_token:
        return await _signup_with_invite(
            session,
            email=email,
            password=password,
            full_name=full_name,
            invite_token=invite_token,
            settings=settings,
            identity=identity,
        )

    if policy.requires_invite:
        raise ForbiddenError(
            "Sign-up requires a valid clinic invite. Ask your clinic administrator."
        )

    if not policy.can_bootstrap_clinic:
        raise ForbiddenError("You cannot create a new clinic on this instance.")

    if not clinic_name or not clinic_slug:
        raise ForbiddenError("clinic_name and clinic_slug are required to register a new clinic.")

    return await _signup_bootstrap_clinic(
        session,
        email=email,
        password=password,
        full_name=full_name,
        clinic_name=clinic_name,
        clinic_slug=clinic_slug,
        identity=identity,
    )


async def _signup_bootstrap_clinic(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    clinic_name: str,
    clinic_slug: str,
    identity: IdentityProvider,
) -> tuple[User, Clinic, str]:
    async with session.begin():
        await session.execute(text("SET LOCAL row_security = off;"))

        existing = await session.execute(select(User.id).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("An account with that email already exists.")
        existing_slug = await session.execute(select(Clinic.id).where(Clinic.slug == clinic_slug))
        if existing_slug.scalar_one_or_none() is not None:
            raise ConflictError("That clinic slug is already taken.")

        user_id = uuid4()
        user = User(id=user_id, email=email, full_name=full_name, is_active=True)
        session.add(user)

        clinic = Clinic(slug=clinic_slug, name=clinic_name)
        session.add(clinic)
        await session.flush()

        await visits_service.ensure_default_prescription_template(session, clinic_id=clinic.id)

        session.add(ClinicMember(clinic_id=clinic.id, user_id=user.id, role=ClinicRole.OWNER))

    _LOCAL_CREDS.set(email, user_id, password)
    token = await identity.issue(user_id=user_id, email=email)
    return user, clinic, token


async def _signup_with_invite(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    invite_token: str,
    settings: Settings,
    identity: IdentityProvider,
) -> tuple[User, Clinic | None, str]:
    async with session.begin():
        await session.execute(text("SET LOCAL row_security = off;"))

        invite = await _resolve_invite_by_token(session, raw_token=invite_token, settings=settings)
        _validate_invite_row(invite, email=email)

        existing = await session.execute(select(User.id).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("An account with that email already exists.")

        user_id = uuid4()
        user = User(id=user_id, email=email, full_name=full_name, is_active=True)
        session.add(user)
        await session.flush()

        session.add(ClinicMember(clinic_id=invite.clinic_id, user_id=user.id, role=invite.role))
        invite.accepted_at = datetime.now(UTC)

        clinic_row = await session.execute(select(Clinic).where(Clinic.id == invite.clinic_id))
        clinic = clinic_row.scalar_one()

    _LOCAL_CREDS.set(email, user_id, password)
    token = await identity.issue(user_id=user_id, email=email)
    return user, clinic, token


async def create_clinic_invite(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    body: InviteCreateRequest,
    invited_by: UUID,
    settings: Settings,
) -> InviteCreated:
    """Issue a single-use invite token for a clinic (shown once to the admin)."""
    ttl = body.expires_in_seconds or settings.invite_default_ttl_seconds
    raw_token = random_token(32)
    token_hmac = hmac_sha256(settings.invite_hmac_secret_value, raw_token)
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
    invite_id = uuid4()

    try:
        pending = await session.execute(
            select(ClinicInvite.id).where(
                ClinicInvite.clinic_id == clinic_id,
                ClinicInvite.email == body.email,
                ClinicInvite.accepted_at.is_(None),
                ClinicInvite.revoked_at.is_(None),
                ClinicInvite.expires_at > datetime.now(UTC),
            )
        )
        if pending.scalar_one_or_none() is not None:
            raise ConflictError("A pending invite already exists for that email.")

        session.add(
            ClinicInvite(
                id=invite_id,
                clinic_id=clinic_id,
                email=body.email,
                role=body.role,
                invited_by=invited_by,
                token_hmac=token_hmac,
                expires_at=expires_at,
            )
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return InviteCreated(
        invite_id=invite_id,
        email=body.email,
        role=body.role.value,
        invite_token=raw_token,
        expires_at=expires_at,
    )


async def list_clinic_invites(
    session: AsyncSession,
    *,
    clinic_id: UUID,
) -> list[InvitePublic]:
    result = await session.execute(
        select(ClinicInvite)
        .where(ClinicInvite.clinic_id == clinic_id)
        .order_by(ClinicInvite.created_at.desc())
    )
    return [
        InvitePublic(
            invite_id=row.id,
            email=row.email,
            role=row.role.value if hasattr(row.role, "value") else str(row.role),
            expires_at=row.expires_at,
            accepted_at=row.accepted_at,
            revoked_at=row.revoked_at,
            created_at=row.created_at,
        )
        for row in result.scalars().all()
    ]


async def revoke_clinic_invite(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    invite_id: UUID,
) -> None:
    row = await session.execute(
        select(ClinicInvite).where(
            ClinicInvite.id == invite_id,
            ClinicInvite.clinic_id == clinic_id,
        )
    )
    invite = row.scalar_one_or_none()
    if invite is None:
        raise NotFoundError("Invite not found.")
    if invite.accepted_at is not None:
        raise ConflictError("Cannot revoke an invite that has already been accepted.")

    invite.revoked_at = datetime.now(UTC)
    session.add(invite)
    await session.commit()


async def change_password(
    session: AsyncSession,
    *,
    user_id: UUID,
    email: str,
    current_password: str,
    new_password: str,
    settings: Settings,
) -> None:
    _ensure_local_identity(settings)
    if _LOCAL_CREDS.verify(email, current_password) is None:
        raise UnauthorizedError("Current password is incorrect.")

    if len(new_password) < 10:
        raise ForbiddenError("New password must be at least 10 characters.")
    if current_password == new_password:
        raise ForbiddenError("New password must be different from the current password.")

    _LOCAL_CREDS.set(email, user_id, new_password)
    async with session.begin():
        await session.execute(text("SET LOCAL row_security = off;"))
        row = await session.execute(select(User).where(User.id == user_id))
        user = row.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User not found.")
        user.last_login_at = datetime.now(UTC)


async def login(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    settings: Settings,
    identity: IdentityProvider,
) -> tuple[User, str]:
    """Verify credentials (local mode), update last_login_at, return token."""
    _ensure_local_identity(settings)

    user_id = _LOCAL_CREDS.verify(email, password)
    if user_id is None:
        raise UnauthorizedError("Invalid email or password.")

    async with session.begin():
        await session.execute(text("SET LOCAL row_security = off;"))
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.last_login_at = datetime.now(UTC)

    token = await identity.issue(user_id=user.id, email=user.email)
    return user, token


def store_password_for_local(email: str, user_id: UUID, password: str) -> None:
    """Used by tests to bootstrap credentials without going through signup."""
    _LOCAL_CREDS.set(email, user_id, password)


def clear_local_credentials() -> None:
    """Reset the local credential store (integration tests + dev scripts)."""
    _LOCAL_CREDS._by_email.clear()
    if _LOCAL_CREDS._path.exists():
        _LOCAL_CREDS._path.unlink()
