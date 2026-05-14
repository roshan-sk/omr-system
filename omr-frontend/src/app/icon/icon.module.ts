import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TablerIconsModule } from 'angular-tabler-icons';
import * as TablerIcons from 'angular-tabler-icons/icons';



@NgModule({
  declarations: [],
  imports: [
    TablerIconsModule.pick(TablerIcons),
    CommonModule
  ],
  exports: [TablerIconsModule]
})
export class IconModule { }
