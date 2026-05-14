import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, tap } from 'rxjs';

const BASE = 'http://localhost:5000';
const WC = { withCredentials: true };

@Injectable({ providedIn: 'root' })
export class AuthService {
  private userSubject = new BehaviorSubject<any>(null);
  currentUser$ = this.userSubject.asObservable();

  constructor(private http: HttpClient) {}

  fetchCurrentUser() {
    return this.http.get<any>(`${BASE}/api/me`, WC).pipe(
      tap(user => this.userSubject.next(user))
    );
  }

  get currentUser() {
    return this.userSubject.value;
  }

  logout() {
    return this.http.post(`${BASE}/logout`, {}, WC).pipe(
      tap(() => this.userSubject.next(null))
    );
  }
}