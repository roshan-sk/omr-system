import {
  MatDialog,
  MatDialogRef,
  MAT_DIALOG_DATA,
} from '@angular/material/dialog';

import { Inject, Optional } from '@angular/core';

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { MaterialModule } from '../../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { AnswerKeyService } from '../../../services/omr/answer-key.service';

import { MatSnackBar } from '@angular/material/snack-bar';

const LEVEL_LABELS: Record<string, string> = {
  lower_primary: 'Lower Primary',
  upper_primary: 'Upper Primary',
  junior: 'Junior',
  intermediate: 'Intermediate',
  senior: 'Senior',
  open: 'Open',
};

@Component({
  selector: 'app-answer-key',
  standalone: true,
  imports: [CommonModule, FormsModule, MaterialModule, TablerIconsModule],
  templateUrl: './answer-key.component.html',
  styleUrls: ['./answer-key.component.scss'],
})
export class AnswerKeyComponent implements OnInit, OnDestroy {
  // ── Validation State ───────────────────────────────────────────────────────

  rangeErrors: number[] = [];
  missingRanges: any[] = [];
  invalidRanges: number[] = [];

  coverageCount = 0;

  // ── Configuration ──────────────────────────────────────────────────────────

  levels = [
    'lower_primary',
    'upper_primary',
    'junior',
    'intermediate',
    'senior',
    'open',
  ];

  selectedLevel = 'intermediate';

  options = ['A', 'B', 'C', 'D', 'E'];

  questions = Array.from({ length: 40 }, (_, i) => {
    const n = String(i + 1).padStart(2, '0');

    return {
      key: `Q${n}`,
      label: `Q${n}`,
    };
  });

  // ── State ──────────────────────────────────────────────────────────────────

  loading = false;

  savingAnswers = false;
  savingRules = false;

  keyData: Record<string, string> = {};
  editData: Record<string, string> = {};

  ranges: any[] = [];

  originalRanges: any[] = [];

  // ── Constructor ────────────────────────────────────────────────────────────

  constructor(
    private answerKeyService: AnswerKeyService,
    private cdr: ChangeDetectorRef,
    private snackBar: MatSnackBar,
    public dialog: MatDialog,
  ) {}

  openConfirmDialog(
    title: string,
    message: string,
    callback: () => void,
  ): void {
    const dialogRef = this.dialog.open(AnswerKeyDialogComponent, {
      width: '420px',
      autoFocus: false,
      data: {
        title,
        message,
      },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result === true) {
        callback();
      }
    });
  }

  // ── Snackbar ───────────────────────────────────────────────────────────────

  openSnackBar(message: string, action: string = 'Close') {
    this.snackBar.open(message, action, {
      duration: 3000,
      horizontalPosition: 'center',
      verticalPosition: 'top',
    });
  }

  // ── Lifecycle ──────────────────────────────────────────────────────────────

  ngOnInit(): void {
    this.loadLevel(this.selectedLevel);
  }

  ngOnDestroy(): void {}

  // ── Level Handling ─────────────────────────────────────────────────────────

  selectLevel(level: string) {
    if (this.selectedLevel === level) {
      return;
    }

    this.selectedLevel = level;

    this.loadLevel(level);
  }

  loadLevel(level: string) {
    this.loading = true;

    this.keyData = {};
    this.editData = {};

    this.ranges = [];
    this.originalRanges = [];

    this.rangeErrors = [];
    this.invalidRanges = [];
    this.missingRanges = [];

    this.cdr.detectChanges();

    this.answerKeyService.getAnswerKey(level).subscribe({
      next: (response: any) => {
        this.keyData = response.answers || {};

        this.editData = {
          ...this.keyData,
        };

        this.ranges = response.scoring_rules || [];

        this.originalRanges = JSON.parse(JSON.stringify(this.ranges));

        this.validateRanges();

        this.loading = false;

        this.cdr.detectChanges();
      },

      error: (err) => {
        console.error('Load error:', err);

        this.openSnackBar(
          'Unable to load answer key data. Please try again.',
        );

        this.loading = false;

        this.cdr.detectChanges();
      },
    });
  }

  // ── Answer Grid ────────────────────────────────────────────────────────────

  selectOption(qKey: string, opt: string) {
    const updated = {
      ...this.editData,
    };

    if (updated[qKey] === opt) {
      delete updated[qKey];
    } else {
      updated[qKey] = opt;
    }

    this.editData = updated;

    this.cdr.detectChanges();
  }

  cancelEdit() {
    this.editData = {
      ...this.keyData,
    };

    this.ranges = JSON.parse(JSON.stringify(this.originalRanges));

    this.validateRanges();

    this.cdr.detectChanges();
  }

  clearAllAnswers(): void {
    this.openConfirmDialog(
      'Clear Answer Keys',
      `Are you sure you want to clear all answer keys for ${this.levelLabel(this.selectedLevel)}?`,
      () => {
        this.savingAnswers = true;

        this.cdr.detectChanges();

        this.answerKeyService.deleteAnswerKeys(this.selectedLevel).subscribe({
          next: () => {
            this.keyData = {};
            this.editData = {};

            this.savingAnswers = false;

            this.openSnackBar('Answer keys deleted successfully.');

            this.cdr.detectChanges();
          },

          error: (err) => {
            console.error(err);

            const msg = err?.error?.error || 'Failed to delete answer keys';

            this.openSnackBar(msg);

            this.savingAnswers = false;

            this.cdr.detectChanges();
          },
        });
      },
    );
  }

  // ── Scoring Rules ──────────────────────────────────────────────────────────

  addRange() {
    this.ranges = [
      ...this.ranges,
      {
        from: 1,
        to: 40,
        correct: 1,
        wrong: 0,
        empty: 0,
      },
    ];

    this.validateRanges();
  }

  removeRange(i: number) {
    this.ranges = this.ranges.filter((_, idx) => idx !== i);

    this.validateRanges();
  }

  deleteAllRules(): void {
    this.openConfirmDialog(
      'Delete Scoring Rules',
      `This will remove all scoring rules for ${this.levelLabel(this.selectedLevel)}.

        After deletion, Sheet evaluation will use default scoring:

        Correct = 1
        Wrong = 0
        Empty = 0

        Do you want to continue?`,
      () => {
        this.answerKeyService.deleteScoringRules(this.selectedLevel).subscribe({
          next: () => {
            this.ranges = [];
            this.originalRanges = [];

            this.validateRanges();

            this.openSnackBar('Scoring rules deleted successfully.');
          },

          error: (err) => {
            const msg = err?.error?.error || 'Failed to delete scoring rules.';
            this.openSnackBar(msg);
          },
        });
      },
    );
  }

  // ── Validation ─────────────────────────────────────────────────────────────

  validateRanges(): void {
    this.rangeErrors = [];
    this.invalidRanges = [];
    this.missingRanges = [];

    const normalized = this.ranges
      .map((r, index) => ({
        index,
        from: Number(r.from),
        to: Number(r.to),
      }))
      .sort((a, b) => a.from - b.from);

    // INVALID RANGE

    normalized.forEach((r) => {
      if (r.from < 1 || r.to > 40 || r.from > r.to) {
        this.invalidRanges.push(r.index);
      }
    });

    // OVERLAP CHECK

    for (let i = 1; i < normalized.length; i++) {
      const prev = normalized[i - 1];
      const curr = normalized[i];

      if (curr.from <= prev.to) {
        this.rangeErrors.push(prev.index);
        this.rangeErrors.push(curr.index);
      }
    }

    // GAP CHECK

    let expected = 1;

    for (const rule of normalized) {
      if (rule.from > expected) {
        this.missingRanges.push({
          start: expected,
          end: rule.from - 1,
        });
      }

      expected = Math.max(expected, rule.to + 1);
    }

    if (expected <= 40) {
      this.missingRanges.push({
        start: expected,
        end: 40,
      });
    }

    // COVERAGE

    const covered = new Set<number>();

    normalized.forEach((r) => {
      for (let q = r.from; q <= r.to; q++) {
        covered.add(q);
      }
    });

    this.coverageCount = covered.size;

    this.cdr.detectChanges();
  }

  // ── Missing Range Helpers ──────────────────────────────────────────────────

  formatMissingRanges(): string {
    return this.missingRanges.map((g) => `${g.start}-${g.end}`).join(', ');
  }

  fillMissingRanges(): void {
    this.missingRanges.forEach((gap) => {
      this.ranges.push({
        from: gap.start,
        to: gap.end,
        correct: 1,
        wrong: 0,
        empty: 0,
      });
    });

    this.ranges.sort((a, b) => a.from - b.from);

    this.validateRanges();
  }

  // ── Save Scoring Rules ─────────────────────────────────────────────────────

  saveScoringRules() {
    if (this.savingRules) {
      return;
    }

    this.validateRanges();

    if (this.rangeErrors.length || this.invalidRanges.length) {
      this.openSnackBar('Please fix invalid or overlapping scoring ranges before saving.');

      return;
    }

    if (this.missingRanges.length) {
      this.openConfirmDialog(
        'Incomplete Coverage',
        `Some questions do not have scoring rules.

          Missing Question Range:
          ${this.formatMissingRanges()}

          Would you like the system to automatically apply default scoring for these questions?

          Default:
          Correct = 1
          Wrong = 0
          Empty = 0`,
        () => {
          this.fillMissingRanges();

          this.saveScoringRules();
        },
      );

      return;
    }

    this.savingRules = true;

    this.cdr.detectChanges();

    const payload = {
      level: this.selectedLevel,
      answers: this.editData,
      scoring_rules: this.ranges,
    };

    this.answerKeyService.saveAnswerKey(payload).subscribe({
      next: () => {
        this.originalRanges = JSON.parse(JSON.stringify(this.ranges));

        this.savingRules = false;

        this.openSnackBar('Scoring rules updated successfully.');

        this.cdr.detectChanges();
      },

      error: (err) => {
        console.error(err);

        const msg = err?.error?.error || 'Failed to save scoring rules';

        this.openSnackBar(msg);

        this.savingRules = false;

        this.cdr.detectChanges();
      },
    });
  }

  // ── Save Answer Keys ───────────────────────────────────────────────────────

  saveAnswerKey() {
    if (this.savingAnswers) {
      return;
    }

    this.savingAnswers = true;

    this.cdr.detectChanges();

    const payload = {
      level: this.selectedLevel,
      answers: this.editData,
      scoring_rules: this.ranges,
    };

    this.answerKeyService.saveAnswerKey(payload).subscribe({
      next: () => {
        this.keyData = {
          ...this.editData,
        };

        this.savingAnswers = false;

        this.openSnackBar('Answer keys updated successfully.');

        this.cdr.detectChanges();
      },

      error: (err) => {
        console.error('Save error:', err);

        const msg = err?.error?.error || 'Failed to save answer key';

        this.openSnackBar(msg);

        this.savingAnswers = false;

        this.cdr.detectChanges();
      },
    });
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

  levelLabel(level: string): string {
    return LEVEL_LABELS[level] || level.replace(/_/g, ' ');
  }

  get setCount(): number {
    return Object.keys(this.editData).length;
  }

  // ── Dirty States ───────────────────────────────────────────────────────────

  get isDirty(): boolean {
    return JSON.stringify(this.editData) !== JSON.stringify(this.keyData);
  }

  get rulesDirty(): boolean {
    return JSON.stringify(this.ranges) !== JSON.stringify(this.originalRanges);
  }
}


@Component({
  selector: 'app-answer-key-dialog',
  standalone: true,
  imports: [
    MaterialModule,
    CommonModule,
    TablerIconsModule,
  ],
  templateUrl: './answer-key-dialog.component.html',
})
export class AnswerKeyDialogComponent {

  constructor(
    public dialogRef: MatDialogRef<AnswerKeyDialogComponent>,
    @Optional()
    @Inject(MAT_DIALOG_DATA)
    public data: any,
  ) {}

  confirm(): void {

    this.dialogRef.close(true);

  }

  closeDialog(): void {

    this.dialogRef.close(false);

  }
}