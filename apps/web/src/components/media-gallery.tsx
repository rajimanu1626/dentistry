import { useEffect, useId, useState } from "react";
import { createPortal } from "react-dom";

export interface MediaGalleryItem {
	id: string;
	kind: string;
	created_at: string;
	signed_url: string;
}

function formatKind(kind: string): string {
	return kind.charAt(0).toUpperCase() + kind.slice(1).replace(/_/g, " ");
}

export function MediaGallery({
	items,
	emptyMessage = "No media yet.",
	selectedId,
	onSelect,
}: {
	items: MediaGalleryItem[];
	emptyMessage?: string;
	selectedId: string | null;
	onSelect: (id: string | null) => void;
}) {
	const dialogId = useId();
	const [mounted, setMounted] = useState(false);
	const selected = items.find((m) => m.id === selectedId) ?? null;

	useEffect(() => {
		setMounted(true);
	}, []);

	useEffect(() => {
		if (!selected) return;
		function onKeyDown(event: KeyboardEvent) {
			if (event.key === "Escape") onSelect(null);
		}
		document.addEventListener("keydown", onKeyDown);
		const prev = document.body.style.overflow;
		document.body.style.overflow = "hidden";
		return () => {
			document.removeEventListener("keydown", onKeyDown);
			document.body.style.overflow = prev;
		};
	}, [selected, onSelect]);

	if (items.length === 0) {
		return <p className="text-sm text-slate-500">{emptyMessage}</p>;
	}

	const modal =
		selected && mounted
			? createPortal(
					<div
						className="fixed inset-0 z-[200] flex items-center justify-center bg-slate-900/75 p-4 backdrop-blur-sm"
						role="presentation"
						onClick={() => onSelect(null)}
					>
						<div
							id={dialogId}
							role="dialog"
							aria-modal="true"
							aria-labelledby={`${dialogId}-title`}
							className="relative flex max-h-[min(90vh,720px)] w-full max-w-2xl flex-col overflow-hidden rounded-lg bg-white shadow-2xl"
							onClick={(e) => e.stopPropagation()}
						>
							<div className="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3">
								<div>
									<p
										id={`${dialogId}-title`}
										className="text-sm font-medium text-slate-900"
									>
										{formatKind(selected.kind)}
									</p>
									<p className="text-xs text-slate-500">
										{new Date(selected.created_at).toLocaleString()}
									</p>
								</div>
								<button
									type="button"
									className="rounded-md px-2 py-1 text-lg leading-none text-slate-500 hover:bg-slate-100 hover:text-slate-800"
									onClick={() => onSelect(null)}
									aria-label="Close preview"
								>
									×
								</button>
							</div>
							<div className="flex min-h-0 flex-1 items-center justify-center bg-slate-50 p-4">
								<img
									src={selected.signed_url}
									alt={`${formatKind(selected.kind)} photo`}
									className="max-h-full max-w-full object-contain"
									draggable={false}
								/>
							</div>
						</div>
					</div>,
					document.body,
				)
			: null;

	return (
		<>
			<p className="mb-2 text-xs text-slate-500">
				{items.length} {items.length === 1 ? "image" : "images"} · click to preview
			</p>
			<ul className="flex flex-wrap gap-1.5">
				{items.map((m) => (
					<li key={m.id}>
						<button
							type="button"
							title={`${formatKind(m.kind)} · ${new Date(m.created_at).toLocaleString()}`}
							className="block h-12 w-12 shrink-0 overflow-hidden rounded border border-slate-200 bg-slate-100 bg-cover bg-center transition hover:border-brand/60 hover:ring-2 hover:ring-brand/20 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
							style={{ backgroundImage: `url("${m.signed_url}")` }}
							onClick={(e) => {
								e.preventDefault();
								e.stopPropagation();
								onSelect(m.id);
							}}
							aria-label={`Preview ${formatKind(m.kind)} image`}
						/>
					</li>
				))}
			</ul>
			{modal}
		</>
	);
}
