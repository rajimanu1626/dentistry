/* eslint-disable */

// @ts-nocheck

// noinspection JSUnusedGlobalSymbols

// This file is based on TanStack Router generated output.
// Keep it excluded from lint/format and edit intentionally when codegen is disabled.

import { Route as rootRouteImport } from './routes/__root';
import { Route as IndexRouteImport } from './routes/index';
import { Route as LoginRouteImport } from './routes/login';
import { Route as PatientsRouteImport } from './routes/patients';
import { Route as PatientsPatientIdRouteImport } from './routes/patients.$patientId';
import { Route as PatientsNewRouteImport } from './routes/patients.new';
import { Route as PlatformRouteImport } from './routes/platform';
import { Route as SettingsSecurityRouteImport } from './routes/settings.security';
import { Route as SettingsTeamRouteImport } from './routes/settings.team';
import { Route as ShareTokenRouteImport } from './routes/share.$token';
import { Route as SignupRouteImport } from './routes/signup';
import { Route as VisitsVisitIdRouteImport } from './routes/visits.$visitId';

const PatientsRoute = PatientsRouteImport.update({
  id: '/patients',
  path: '/patients',
  getParentRoute: () => rootRouteImport,
});
const IndexRoute = IndexRouteImport.update({
  id: '/',
  path: '/',
  getParentRoute: () => rootRouteImport,
});
const LoginRoute = LoginRouteImport.update({
  id: '/login',
  path: '/login',
  getParentRoute: () => rootRouteImport,
});
const PlatformRoute = PlatformRouteImport.update({
  id: '/platform',
  path: '/platform',
  getParentRoute: () => rootRouteImport,
});
const SignupRoute = SignupRouteImport.update({
  id: '/signup',
  path: '/signup',
  getParentRoute: () => rootRouteImport,
});
const SettingsTeamRoute = SettingsTeamRouteImport.update({
  id: '/settings/team',
  path: '/settings/team',
  getParentRoute: () => rootRouteImport,
});
const SettingsSecurityRoute = SettingsSecurityRouteImport.update({
  id: '/settings/security',
  path: '/settings/security',
  getParentRoute: () => rootRouteImport,
});
const ShareTokenRoute = ShareTokenRouteImport.update({
  id: '/share/$token',
  path: '/share/$token',
  getParentRoute: () => rootRouteImport,
});
const PatientsNewRoute = PatientsNewRouteImport.update({
  id: '/patients/new',
  path: '/patients/new',
  getParentRoute: () => rootRouteImport,
});
const PatientsPatientIdRoute = PatientsPatientIdRouteImport.update({
  id: '/patients/$patientId',
  path: '/patients/$patientId',
  getParentRoute: () => rootRouteImport,
});
const VisitsVisitIdRoute = VisitsVisitIdRouteImport.update({
  id: '/visits/$visitId',
  path: '/visits/$visitId',
  getParentRoute: () => rootRouteImport,
});

export interface FileRoutesByFullPath {
  '/': typeof IndexRoute;
  '/login': typeof LoginRoute;
  '/platform': typeof PlatformRoute;
  '/signup': typeof SignupRoute;
  '/patients': typeof PatientsRoute;
  '/patients/$patientId': typeof PatientsPatientIdRoute;
  '/patients/new': typeof PatientsNewRoute;
  '/visits/$visitId': typeof VisitsVisitIdRoute;
  '/settings/team': typeof SettingsTeamRoute;
  '/settings/security': typeof SettingsSecurityRoute;
  '/share/$token': typeof ShareTokenRoute;
}
export interface FileRoutesByTo {
  '/': typeof IndexRoute;
  '/login': typeof LoginRoute;
  '/platform': typeof PlatformRoute;
  '/signup': typeof SignupRoute;
  '/patients': typeof PatientsRoute;
  '/patients/$patientId': typeof PatientsPatientIdRoute;
  '/patients/new': typeof PatientsNewRoute;
  '/visits/$visitId': typeof VisitsVisitIdRoute;
  '/settings/team': typeof SettingsTeamRoute;
  '/settings/security': typeof SettingsSecurityRoute;
  '/share/$token': typeof ShareTokenRoute;
}
export interface FileRoutesById {
  __root__: typeof rootRouteImport;
  '/': typeof IndexRoute;
  '/login': typeof LoginRoute;
  '/platform': typeof PlatformRoute;
  '/signup': typeof SignupRoute;
  '/patients': typeof PatientsRoute;
  '/patients/$patientId': typeof PatientsPatientIdRoute;
  '/patients/new': typeof PatientsNewRoute;
  '/visits/$visitId': typeof VisitsVisitIdRoute;
  '/settings/team': typeof SettingsTeamRoute;
  '/settings/security': typeof SettingsSecurityRoute;
  '/share/$token': typeof ShareTokenRoute;
}
export interface FileRouteTypes {
  fileRoutesByFullPath: FileRoutesByFullPath;
  fullPaths:
    | '/'
    | '/login'
    | '/platform'
    | '/signup'
    | '/patients'
    | '/patients/$patientId'
    | '/patients/new'
    | '/visits/$visitId'
    | '/settings/team'
    | '/settings/security'
    | '/share/$token';
  fileRoutesByTo: FileRoutesByTo;
  to:
    | '/'
    | '/login'
    | '/platform'
    | '/signup'
    | '/patients'
    | '/patients/$patientId'
    | '/patients/new'
    | '/visits/$visitId'
    | '/settings/team'
    | '/settings/security'
    | '/share/$token';
  id:
    | '__root__'
    | '/'
    | '/login'
    | '/platform'
    | '/signup'
    | '/patients'
    | '/patients/$patientId'
    | '/patients/new'
    | '/visits/$visitId'
    | '/settings/team'
    | '/settings/security'
    | '/share/$token';
  fileRoutesById: FileRoutesById;
}
export interface RootRouteChildren {
  IndexRoute: typeof IndexRoute;
  LoginRoute: typeof LoginRoute;
  PlatformRoute: typeof PlatformRoute;
  SignupRoute: typeof SignupRoute;
  PatientsRoute: typeof PatientsRoute;
  PatientsPatientIdRoute: typeof PatientsPatientIdRoute;
  PatientsNewRoute: typeof PatientsNewRoute;
  VisitsVisitIdRoute: typeof VisitsVisitIdRoute;
  SettingsTeamRoute: typeof SettingsTeamRoute;
  SettingsSecurityRoute: typeof SettingsSecurityRoute;
  ShareTokenRoute: typeof ShareTokenRoute;
}

declare module '@tanstack/react-router' {
  interface FileRoutesByPath {
    '/patients': {
      id: '/patients';
      path: '/patients';
      fullPath: '/patients';
      preLoaderRoute: typeof PatientsRouteImport;
      parentRoute: typeof rootRouteImport;
    };
    '/': {
      id: '/';
      path: '/';
      fullPath: '/';
      preLoaderRoute: typeof IndexRouteImport;
      parentRoute: typeof rootRouteImport;
    };
    '/login': {
      id: '/login';
      path: '/login';
      fullPath: '/login';
      preLoaderRoute: typeof LoginRouteImport;
      parentRoute: typeof rootRouteImport;
    };
    '/platform': {
      id: '/platform';
      path: '/platform';
      fullPath: '/platform';
      preLoaderRoute: typeof PlatformRouteImport;
      parentRoute: typeof rootRouteImport;
    };
    '/signup': {
      id: '/signup';
      path: '/signup';
      fullPath: '/signup';
      preLoaderRoute: typeof SignupRouteImport;
      parentRoute: typeof rootRouteImport;
    };
    '/settings/team': {
      id: '/settings/team';
      path: '/settings/team';
      fullPath: '/settings/team';
      preLoaderRoute: typeof SettingsTeamRouteImport;
      parentRoute: typeof rootRouteImport;
    };
    '/settings/security': {
      id: '/settings/security';
      path: '/settings/security';
      fullPath: '/settings/security';
      preLoaderRoute: typeof SettingsSecurityRouteImport;
      parentRoute: typeof rootRouteImport;
    };
    '/share/$token': {
      id: '/share/$token';
      path: '/share/$token';
      fullPath: '/share/$token';
      preLoaderRoute: typeof ShareTokenRouteImport;
      parentRoute: typeof rootRouteImport;
    };
    '/visits/$visitId': {
      id: '/visits/$visitId';
      path: '/visits/$visitId';
      fullPath: '/visits/$visitId';
      preLoaderRoute: typeof VisitsVisitIdRouteImport;
      parentRoute: typeof rootRouteImport;
    };
    '/patients/new': {
      id: '/patients/new';
      path: '/patients/new';
      fullPath: '/patients/new';
      preLoaderRoute: typeof PatientsNewRouteImport;
      parentRoute: typeof rootRouteImport;
    };
    '/patients/$patientId': {
      id: '/patients/$patientId';
      path: '/patients/$patientId';
      fullPath: '/patients/$patientId';
      preLoaderRoute: typeof PatientsPatientIdRouteImport;
      parentRoute: typeof rootRouteImport;
    };
  }
}

const rootRouteChildren: RootRouteChildren = {
  IndexRoute: IndexRoute,
  LoginRoute: LoginRoute,
  PlatformRoute: PlatformRoute,
  SignupRoute: SignupRoute,
  PatientsRoute: PatientsRoute,
  PatientsPatientIdRoute: PatientsPatientIdRoute,
  PatientsNewRoute: PatientsNewRoute,
  VisitsVisitIdRoute: VisitsVisitIdRoute,
  SettingsTeamRoute: SettingsTeamRoute,
  SettingsSecurityRoute: SettingsSecurityRoute,
  ShareTokenRoute: ShareTokenRoute,
};
export const routeTree = rootRouteImport
  ._addFileChildren(rootRouteChildren)
  ._addFileTypes<FileRouteTypes>();
