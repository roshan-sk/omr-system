import { Routes } from '@angular/router';
import { BlankComponent } from './layouts/blank/blank.component';
import { FullComponent } from './layouts/full/full.component';

import { authGuard } from './services/omr/auth.guard';
import { adminGuard } from './services/omr/admin.guard';

export const routes: Routes = [
  {
    path: '',
    component: FullComponent,
    children: [
      {
        path: '',
        redirectTo: '/authentication/login',
        pathMatch: 'full',
      },
      {
        path: 'analyzer',

        canActivate: [authGuard],

        data: {
          title: 'OMR Analyzer',
          urls: [
            { title: 'Dashboard', url: '/analyzer' },
            { title: 'Upload OMR Sheets' },
          ],
        },

        loadComponent: () =>
          import('./pages/omr/analyzer/analyzer.component').then(
            (m) => m.AnalyzerComponent,
          ),
      },
      {
        path: 'answer-key',

        canActivate: [authGuard],

        data: {
          title: 'Answer Key',
          urls: [
            { title: 'Dashboard', url: '/analyzer' },
            { title: 'Answer Key' },
          ],
        },

        loadComponent: () =>
          import('./pages/omr/answer-key/answer-key.component').then(
            (m) => m.AnswerKeyComponent,
          ),
      },
      {
        path: 'users',

        canActivate: [adminGuard],
        
        data: {
          title: 'Users Management',
          urls: [
            { title: 'Dashboard', url: '/analyzer' },
            { title: 'Users' },
          ],
        },

        loadComponent: () =>
          import('./pages/omr/users/users.component').then(
            (m) => m.UsersComponent,
          ),
      },
    ],
  },
  {
    path: '',
    component: BlankComponent,
    children: [
      {
        path: 'authentication',
        loadChildren: () =>
          import('./pages/authentication/authentication.routes').then(
            (m) => m.AuthenticationRoutes,
          ),
      },
    ],
  },
  {
    path: '**',
    redirectTo: 'authentication/error',
  },
];
