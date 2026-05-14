import { NavItem } from './nav-item/nav-item';

export const navItems: NavItem[] = [
  {
    navCap: 'Home',
  },
  {
    displayName: 'Analyzer',
    iconName: 'file-analytics',
    route: '/analyzer',
  },
  {
    displayName: 'Answer Key',
    iconName: 'key',
    route: '/answer-key',
  },
  {
    displayName: 'Users',
    iconName: 'users',
    route: '/users',

    adminOnly: true, // admin only view this
  },
];
