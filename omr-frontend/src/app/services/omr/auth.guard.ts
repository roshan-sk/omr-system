import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AuthService } from './auth.service';
import { map, catchError, of } from 'rxjs';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const snackBar = inject(MatSnackBar);

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
    return true;
  }

  // Hard refresh case
  return auth.fetchCurrentUser().pipe(
    map(() => true),

    catchError(() => {
      showLoginRequired();

      return of(router.createUrlTree(['/authentication/login']));
    }),
  );
};
