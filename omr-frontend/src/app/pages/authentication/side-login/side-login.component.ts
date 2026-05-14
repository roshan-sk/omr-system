import { Component, ChangeDetectorRef } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../../material.module';
import { BrandingComponent } from '../../../layouts/full/vertical/sidebar/branding.component';

@Component({
  selector: 'app-side-login',
  standalone: true,
  imports: [RouterModule, MaterialModule, FormsModule, CommonModule, BrandingComponent],
  templateUrl: './side-login.component.html',
})
export class AppSideLoginComponent {
  email = '';
  password = '';
  loading = false;
  errorMessage = '';
  showPassword = false;

  constructor(
    private router: Router,
    private http: HttpClient,
    private cdr: ChangeDetectorRef
  ) {}

  login() {
    this.loading = true;
    this.errorMessage = '';

    this.http
      .post('http://localhost:5000/login', { email: this.email, password: this.password }, { withCredentials: true })
      .subscribe({
        next: () => {
          this.loading = false;
          this.router.navigate(['/analyzer']); // change this later to /analyzer
        },
        error: (error) => {
          this.loading = false;
          this.errorMessage =
            error?.error?.msg ||
            error?.error?.message ||
            'Invalid email or password. Please try again.';
          this.cdr.detectChanges();
        },
      });
  }
}