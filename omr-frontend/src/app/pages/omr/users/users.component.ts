import {
  Component,
  Inject,
  Optional,
  ViewChild,
  AfterViewInit,
  OnInit,
} from '@angular/core';

import { MatTableDataSource, MatTable } from '@angular/material/table';
import { MatPaginator } from '@angular/material/paginator';
import {
  MatDialog,
  MatDialogRef,
  MAT_DIALOG_DATA,
} from '@angular/material/dialog';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MaterialModule } from 'src/app/material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { CommonModule } from '@angular/common';
import { MatSnackBar } from '@angular/material/snack-bar';
import { UserService } from 'src/app/services/omr/user.service';

export interface User {
  id?: number;
  username: string;
  email: string;
  password?: string;
  role: string;
  is_active: boolean;
  scanned_sheets_count?: number;
}

@Component({
  selector: 'app-users',
  standalone: true,
  templateUrl: './users.component.html',
  imports: [
    MaterialModule,
    FormsModule,
    ReactiveFormsModule,
    TablerIconsModule,
    CommonModule,
  ],
})
export class UsersComponent implements OnInit, AfterViewInit {
  @ViewChild(MatTable, { static: true }) table: MatTable<any> =
    Object.create(null);

  @ViewChild(MatPaginator, { static: true }) paginator: MatPaginator =
    Object.create(null);

  displayedColumns: string[] = [
    'index',
    'username',
    'email',
    'role',
    'status',
    'scanned',
    'action',
  ];

  dataSource = new MatTableDataSource<User>([]);

  loading = false;
  // errorMessage = '';

  constructor(
    public dialog: MatDialog,
    private userService: UserService,
    private snackBar: MatSnackBar,
  ) {}

  openSnackBar(message: string, action: string = 'Close') {
    this.snackBar.open(message, action, {
      duration: 3000,
      horizontalPosition: 'center',
      verticalPosition: 'top',
    });
  }

  ngOnInit(): void {
    this.loadUsers();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
  }

  loadUsers(): void {
    this.loading = true;
    // this.errorMessage = '';
    this.userService.getUsers().subscribe({
      next: (res: any) => {
        const users: User[] = res || [];
        this.dataSource = new MatTableDataSource(users);
        this.dataSource.paginator = this.paginator;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.openSnackBar(err?.error?.msg || 'Failed to load users.');
      },
    });
  }

  applyFilter(filterValue: string): void {
    this.dataSource.filter = filterValue.trim().toLowerCase();
  }

  openDialog(action: string, user: User | any): void {
    const dialogRef = this.dialog.open(UserDialogContentComponent, {
      data: { action, user },
      autoFocus: false,
      width: '500px',
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result && result.event !== 'Cancel') {
        this.loadUsers();
      }
    });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Dialog component
// ─────────────────────────────────────────────────────────────────────────────

interface DialogData {
  action: string;
  user: User;
}

@Component({
  selector: 'app-user-dialog-content',
  standalone: true,
  imports: [
    MaterialModule,
    FormsModule,
    ReactiveFormsModule,
    CommonModule,
    TablerIconsModule,
  ],
  templateUrl: './users-dialog-content.html',
})
export class UserDialogContentComponent {
  action: string;
  local_data: User;
  showPassword = false;

  constructor(
    public dialogRef: MatDialogRef<UserDialogContentComponent>,
    private userService: UserService,
    private snackBar: MatSnackBar,
    @Optional() @Inject(MAT_DIALOG_DATA) public data: DialogData,
  ) {
    this.action = data.action;
    this.local_data = { ...data.user };
    if (!this.local_data.role) this.local_data.role = 'USER';
    if (this.local_data.is_active === undefined)
      this.local_data.is_active = true;
  }

  doAction(): void {
    if (this.action === 'Add') {
      this.userService.createUser(this.local_data).subscribe({
        next: () => {
          this.dialogRef.close({ event: 'Add' });
          this.openSnackBar('User added successfully!', 'Close');
        },
        error: (e) => {
          this.openSnackBar(e?.error?.msg || 'Failed to add user.', 'Close');
        },
      });
    } else if (this.action === 'Update') {
      const payload: any = {
        username: this.local_data.username,
        email: this.local_data.email,
        role: this.local_data.role,
        is_active: this.local_data.is_active,
      };
      if (this.local_data.password) payload.password = this.local_data.password;
      this.userService.updateUser(this.local_data.id!, payload).subscribe({
        next: () => {
          this.dialogRef.close({ event: 'Update' });
          this.openSnackBar('User updated successfully!', 'Close');
        },
        error: (e) => {
          this.openSnackBar(e?.error?.msg || 'Failed to update user.', 'Close');
        },
      });
    } else if (this.action === 'Delete') {
      this.userService.deleteUser(this.local_data.id!).subscribe({
        next: () => {
          this.dialogRef.close({ event: 'Delete' });
          this.openSnackBar('User deleted successfully!', 'Close');
        },
        error: (e) => {
          this.openSnackBar(e?.error?.msg || 'Failed to delete user.', 'Close');
        },
      });
    }
  }

  openSnackBar(message: string, action: string) {
    this.snackBar.open(message, action, {
      duration: 3000,
      horizontalPosition: 'center',
      verticalPosition: 'top',
    });
  }

  closeDialog(): void {
    this.dialogRef.close({ event: 'Cancel' });
  }
}
