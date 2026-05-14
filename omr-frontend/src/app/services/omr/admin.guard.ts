import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AuthService } from './auth.service';
import { map, catchError, of } from 'rxjs';

export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const snackBar = inject(MatSnackBar);

  const showAccessDenied = () => {
    snackBar.open(
      "Access denied. You don't have permission to access Users page.",
      'Close',
      {
        duration: 3000,
        horizontalPosition: 'center',
        verticalPosition: 'top',
        panelClass: ['error-snackbar'],
      },
    );
  };

  const showLoginRequired = () => {
    snackBar.open('Please login to continue.', 'Close', {
      duration: 3000,
      horizontalPosition: 'center',
      verticalPosition: 'top',
      panelClass: ['warning-snackbar'],
    });
  };

  // User already available in memory
  if (auth.currentUser) {
    if (auth.currentUser.role === 'ADMIN') {
      return true;
    }

    showAccessDenied();
    return router.createUrlTree(['/analyzer']);
  }

  // Hard refresh case
  return auth.fetchCurrentUser().pipe(
    map((user) => {
      if (user?.role === 'ADMIN') {
        return true;
      }

      showAccessDenied();
      return router.createUrlTree(['/analyzer']);
    }),

    catchError(() => {
      showLoginRequired();
      return of(router.createUrlTree(['/authentication/login']));
    }),
  );
};
