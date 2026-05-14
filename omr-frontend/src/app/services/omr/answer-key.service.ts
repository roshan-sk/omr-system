
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

const BASE = 'http://localhost:5000';

const WC = {
  withCredentials: true,
};

@Injectable({
  providedIn: 'root',
})
export class AnswerKeyService {
  constructor(private http: HttpClient) {}

  // ── Get Answer Key ─────────────────────────────────────────────────────────
  getAnswerKey(level: string) {
    return this.http.get(`${BASE}/api/get_answer_key/${level}`, WC);
  }

  // ── Save Answer Key + Scoring Rules ───────────────────────────────────────
  saveAnswerKey(data: any) {
    return this.http.post(`${BASE}/api/save_answer_key`, data, WC);
  }

  // ── Delete All Scoring Rules ───────────────────────────────────────────────
  deleteScoringRules(level: string) {
    return this.http.delete(`${BASE}/api/delete_scoring_rules/${level}`, WC);
  }

  // ── Delete Answer Keys ───────────────────────────────────────────────
  deleteAnswerKeys(level: string) {
    return this.http.delete(`${BASE}/api/delete_answer_keys/${level}`, WC);
  }
}
