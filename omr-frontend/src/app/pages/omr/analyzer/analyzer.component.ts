import {
  Component,
  OnDestroy,
  ChangeDetectorRef,
  ViewChild,
  AfterViewInit,
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';

import { MaterialModule } from '../../../material.module';

import { MatSnackBar } from '@angular/material/snack-bar';

const BASE = 'http://localhost:5000';
const WC = { withCredentials: true };

const LEVEL_LABELS: Record<string, string> = {
  lower_primary: 'Lower Primary',
  upper_primary: 'Upper Primary',
  junior: 'Junior',
  intermediate: 'Intermediate',
  senior: 'Senior',
  open: 'Open',
};

@Component({
  selector: 'app-analyzer',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MaterialModule,
    MatPaginatorModule,
    MatTableModule,
  ],
  templateUrl: './analyzer.component.html',
  styleUrls: ['./analyzer.component.scss'],
})
export class AnalyzerComponent implements AfterViewInit, OnDestroy {
  private _paginator!: MatPaginator;

  @ViewChild(MatPaginator)
  set paginator(value: MatPaginator) {
    this._paginator = value;
    if (value) {
      this.dataSource.paginator = value;
    }
  }

  displayedColumns: string[] = [
    'index',
    'name',
    'centre',
    'level',
    'dob',
    'score',
    'action',
  ];

  dataSource = new MatTableDataSource<any>([]);

  selectedFiles: File[] = [];
  isDragging = false;
  isProcessing = false;
  progressPct = 0;
  progressText = '';
  liveCount = 0;

  private batchId = '';
  private pollTimer: any = null;
  private offset = 0;

  allResults: Record<string, any> = {};
  resultRows: any[] = [];
  searchQuery = '';

  modalOpen = false;
  modalStudent: any = null;

  constructor(
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
    private snackBar: MatSnackBar,
  ) {}

  openSnackBar(message: string, action: string = 'Close') {
    this.snackBar.open(message, action, {
      duration: 3000,
      horizontalPosition: 'center',
      verticalPosition: 'top',
    });
  }

  ngAfterViewInit(): void {
    this.dataSource.filterPredicate = (row: any, filter: string) => {
      return (
        (row.name || '').toLowerCase().includes(filter) ||
        (row.centre_number || '').toLowerCase().includes(filter)
      );
    };
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  onFileSelected(event: any) {
    const files: FileList = event.target.files;
    if (!files) return;
    Array.from(files).forEach((file) => {
      if (!this.selectedFiles.some((f) => f.name === file.name))
        this.selectedFiles.push(file);
    });
  }

  removeFile(index: number) {
    this.selectedFiles.splice(index, 1);
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
    const files = event.dataTransfer?.files;
    if (!files) return;
    Array.from(files).forEach((file) => {
      if (!this.selectedFiles.some((f) => f.name === file.name))
        this.selectedFiles.push(file);
    });
  }

  processFiles() {
    if (!this.selectedFiles.length || this.isProcessing) return;

    this.resetUI();

    this.http
      .post<{ batch_id: string }>(`${BASE}/api/start`, {}, WC)
      .subscribe({
        next: (res) => {
          this.batchId = res.batch_id;
          const formData = new FormData();
          this.selectedFiles.forEach((f) => formData.append('files', f));
          formData.append('batch_id', this.batchId);

          this.http.post(`${BASE}/api/upload`, formData, WC).subscribe({
            next: () => this.startPolling(),
            error: () => {
              this.openSnackBar('Upload failed.');
              this.reset();
            },
          });
        },
        error: (error) => {
          this.openSnackBar(
            error?.error?.msg ||
              error?.error?.message ||
              'Could not start processing.',
          );
          this.reset();
        },
      });
  }

  resetUI() {
    this.isProcessing = true;
    this.progressPct = 0;
    this.progressText = 'Starting...';
    this.liveCount = 0;
    this.offset = 0;
    this.allResults = {};
    this.resultRows = [];
    this.dataSource.data = [];
    this.searchQuery = '';
  }

  startPolling() {
    this.pollTimer = setInterval(() => this.poll(), 1200);
  }

  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  poll() {
    this.http
      .get<any>(`${BASE}/api/results/${this.batchId}?offset=${this.offset}`, WC)
      .subscribe({
        next: (data) => {
          this.progressPct = data.percent ?? 0;
          this.progressText = data.status ?? 'Processing...';
          this.liveCount += (data.results ?? []).length;
          this.offset = data.offset ?? this.offset;
          this.appendRows(data.results ?? []);

          const status = (data.status ?? '').toLowerCase();

          if (status === 'completed') {
            this.stopPolling();
            this.isProcessing = false;
            this.progressPct = 100;
            this.progressText = 'Completed';
            const note = (data.completion_note || '').trim();
            this.openSnackBar(
              note
                ? `Done — ${this.liveCount} sheet(s) processed. Issues: ${note}`
                : `Done — ${this.liveCount} sheet(s) processed`,
              note ? 'Dismiss' : 'Close',
            );
            this.selectedFiles = [];
            this.cdr.detectChanges();
          }

          if (status === 'failed') {
            this.openSnackBar('Processing failed');
            this.reset();
          }
        },
        error: () => {
          this.openSnackBar('Connection lost');
          this.reset();
        },
      });
  }

  reset() {
    this.stopPolling();
    this.isProcessing = false;
    this.progressPct = 0;
    this.progressText = '';
    this.liveCount = 0;
    this.cdr.detectChanges();
  }

  appendRows(results: any[]) {
    if (!results.length) return;

    results.forEach((r) => {
      if (this.allResults[r.key]) return;
      this.allResults[r.key] = r;
      this.resultRows.push(r);
    });

    this.dataSource.data = [...this.resultRows];
    this.cdr.detectChanges();
  }

  onSearch(query: string) {
    this.searchQuery = query;
    this.dataSource.filter = query.trim().toLowerCase();
    if (this.dataSource.paginator) this.dataSource.paginator.firstPage();
  }


  get statTotal(): number {
    return this.resultRows.length;
  }

  get statAvg(): string {
    if (!this.resultRows.length) return '—';
    const avg =
      this.resultRows
        .map((r) => parseFloat(r.percentage) || 0)
        .reduce((s, v) => s + v, 0) / this.resultRows.length;
    return avg.toFixed(1) + '%';
  }

  get statHigh(): string {
    if (!this.resultRows.length) return '—';
    return (
      Math.max(
        ...this.resultRows.map((r) => parseFloat(r.percentage) || 0),
      ).toFixed(1) + '%'
    );
  }


  levelLabel(lv: string): string {
    return LEVEL_LABELS[lv] || lv || '—';
  }
  levelClass(lv: string): string {
    return 'lv-badge lv-' + lv;
  }

  scoreClass(pct: number): string {
    if (pct >= 75) return 'score-g';
    if (pct >= 50) return 'score-y';
    return 'score-r';
  }

  rowIndex(r: any): string {
    return String(this.resultRows.indexOf(r) + 1).padStart(2, '0');
  }

  normalizedLevel(r: any): string {
    return (r.level || '').toLowerCase().replace(/\s+/g, '_');
  }

  emptyCount(r: any): number {
    if (r.empty !== undefined) return r.empty;
    return (r.answers || []).filter(
      (a: any) => !a.value || (a.value || '').toLowerCase() === 'empty',
    ).length;
  }


  viewResult(key: string) {
    const row = this.allResults[key];
    if (!row) return;
    this.modalStudent = row;
    this.modalOpen = true;
  }

  closeModal() {
    this.modalOpen = false;
    this.modalStudent = null;
  }

  nameInitial(name: string): string {
    return name ? name.trim()[0].toUpperCase() : '?';
  }

  modalMetaLine(): string {
    if (!this.modalStudent) return '';
    const lv = this.normalizedLevel(this.modalStudent);
    return [
      this.modalStudent.centre_number,
      this.levelLabel(lv),
      this.modalStudent.dob,
    ]
      .filter(Boolean)
      .join('  ·  ');
  }

  modalPctColor(): string {
    const pct = parseFloat(this.modalStudent?.percentage) || 0;
    if (pct >= 75) return '#16a34a';
    if (pct >= 50) return '#d97706';
    return '#dc2626';
  }

  modalAnswers(): any[] {
    return this.modalStudent?.answers || [];
  }

  pillClass(a: any): string {
    const val = (a.value || '').trim();
    if (val.toLowerCase().includes('multiple')) return 'pill pill-multi';
    if (!val || val.toLowerCase() === 'empty') return 'pill pill-empty';
    if (a.is_correct) return 'pill pill-correct';
    return 'pill pill-wrong';
  }

  pillDisplay(a: any): string {
    const val = (a.value || '').trim();
    if (!val || val.toLowerCase() === 'empty') return '—';
    return val;
  }

  modalCorrect(): number {
    return this.modalStudent?.correct || 0;
  }
  modalWrong(): number {
    return this.modalStudent?.wrong || 0;
  }
  modalEmpty(): number {
    return this.emptyCount(this.modalStudent || {});
  }

  onExport() {
    if (!this.batchId) {
      this.openSnackBar('No processed batch available');
      return;
    }

    this.http
      .get(`${BASE}/api/export_latest?batch_id=${this.batchId}`, {
        ...WC,
        responseType: 'blob',
      })
      .subscribe({
        next: (blob) => {
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `OMR_Results_${this.batchId.slice(0, 8)}.xlsx`;
          a.click();
          URL.revokeObjectURL(url);
        },
        error: (err) => {
          this.openSnackBar('Export failed. Please try again.');
          console.error(err);
        },
      });
  }
}
