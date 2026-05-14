import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { MaterialModule } from '../../../material.module';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-maintenance',
  imports: [RouterModule, MaterialModule, MatButtonModule],
  templateUrl: './maintenance.component.html',
})
export class AppMaintenanceComponent {}
