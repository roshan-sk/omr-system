import { Component, ChangeDetectorRef } from '@angular/core';
import { CoreService } from 'src/app/services/core.service';
import {
  FormGroup,
  FormControl,
  Validators,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../../material.module';
import { BrandingComponent } from '../../../layouts/full/vertical/sidebar/branding.component';

@Component({
  selector: 'app-boxed-login',
  imports: [
    RouterModule,
    MaterialModule,
    FormsModule,
    ReactiveFormsModule,
    CommonModule,
    BrandingComponent,
  ],
  templateUrl: './boxed-login.component.html',
})
export class AppBoxedLoginComponent {
  options = this.settings.getOptions();

  showPassword = false;
  loading = false;
  errorMessage = '';

  constructor(
    private settings: CoreService,
    private router: Router,
    private http: HttpClient,
    private cdr: ChangeDetectorRef
  ) {}

  form = new FormGroup({
    uname: new FormControl('', [Validators.required, Validators.minLength(6)]),
    password: new FormControl('', [Validators.required]),
  });

  get f() {
    return this.form.controls;
  }

  submit() {
    if (this.form.invalid) return;

    this.loading = true;
    this.errorMessage = '';

    this.http
      .post(
        'http://localhost:5000/login',
        { email: this.f['uname'].value, password: this.f['password'].value },
        { withCredentials: true }
      )
      .subscribe({
        next: () => {
          this.loading = false;
          this.router.navigate(['/analyzer']);
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