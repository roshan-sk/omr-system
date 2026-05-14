import {
  Component,
  OnInit,
  Input,
} from '@angular/core';
import { Router } from '@angular/router';
import { NavService } from '../../../../../services/nav.service';
import { TablerIconsModule } from 'angular-tabler-icons';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from 'src/app/services/omr/auth.service'; // admin view only

@Component({
    selector: 'app-horizontal-nav-item',
    imports: [TablerIconsModule, CommonModule, MatIconModule],
    templateUrl: './nav-item.component.html'
})
export class AppHorizontalNavItemComponent implements OnInit {
  @Input() depth: any;
  @Input() item: any;

  constructor(public navService: NavService, public router: Router, public authService: AuthService) {
    if (this.depth === undefined) {
      this.depth = 0;
    }
  }

  get isAdmin(): boolean {
    return this.authService.currentUser?.role === 'ADMIN';
  } // admin acess

  ngOnInit() { }
  onItemSelected(item: any) {
    if (!item.children || !item.children.length) {
      this.router.navigate([item.route]);
    }
  }
}
