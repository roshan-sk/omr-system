import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

const BASE = 'http://localhost:5000';
const WC = { withCredentials: true };

@Injectable({
  providedIn: 'root',
})
export class UserService {
  constructor(private http: HttpClient) {}

  getUsers() {
    return this.http.get(`${BASE}/admin/users`, WC);
  }

  createUser(data: any) {
    return this.http.post(`${BASE}/admin/users`, data, WC);
  }

  updateUser(userId: number, data: any) {
    return this.http.put(`${BASE}/admin/users/${userId}`, data, WC);
  }

  deleteUser(userId: number) {
    return this.http.delete(`${BASE}/admin/users/${userId}`, WC);
  }
}