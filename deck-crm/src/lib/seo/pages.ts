import type { SeoConfig } from './seo';

export type BreadcrumbItem = {
  label: string;
  href: string;
};

export const publicSeoPages: Record<string, SeoConfig> = {
  '/': {
    title: 'AI Pitch Deck Redesign for Founders',
    description:
      'deck.aistack.codes helps founders, consultants, and venture teams turn existing decks into investor-ready presentations with AI-assisted review, brand extraction, and export workflows.',
    canonicalPath: '/',
    keywords: [
      'AI pitch deck',
      'pitch deck redesign',
      'startup deck review',
      'investor deck AI',
      'presentation design AI'
    ]
  },
  '/about': {
    title: 'About deck.aistack.codes',
    description:
      'Learn how deck.aistack.codes approaches investor-grade deck adaptation, reviewable AI editing, and structured presentation workflows.',
    canonicalPath: '/about'
  },
  '/pricing': {
    title: 'Pricing',
    description:
      'Request access to deck.aistack.codes and discuss AI-assisted pitch deck redesign, investor-readiness review, and Smart Deck transformation workflows.',
    canonicalPath: '/pricing'
  },
  '/contact': {
    title: 'Contact deck.aistack.codes',
    description:
      'Contact deck.aistack.codes for pilot inquiries, product walkthroughs, and investor deck workflow discussions.',
    canonicalPath: '/contact'
  },
  '/privacy': {
    title: 'Privacy Policy',
    description:
      'Read how deck.aistack.codes handles uploaded decks, logos, brand assets, AI-assisted outputs, private AI access, account data, and contact submissions.',
    canonicalPath: '/privacy'
  },
  '/terms': {
    title: 'Terms of Service',
    description:
      'Review the deck.aistack.codes terms covering product usage, uploaded deck data, and reviewable AI-assisted editing workflows.',
    canonicalPath: '/terms'
  },
  '/vcs': {
    title: 'For VCs',
    description:
      'See how deck.aistack.codes supports IC preparation, partner review, and audience-specific deck adaptation for venture teams.',
    canonicalPath: '/vcs'
  },
  '/billing': {
    title: 'Billing',
    description:
      'Review deck.aistack.codes commercial packaging for investor-grade review workflows before becoming a full workspace user.',
    canonicalPath: '/billing'
  },
  '/auth/sign-in': {
    title: 'Sign In',
    description:
      'Sign in to deck.aistack.codes to continue into Smart Deck intake and the investor-grade deck workspace.',
    canonicalPath: '/auth/sign-in'
  },
  '/auth/sign-up': {
    title: 'Create a Workspace',
    description:
      'Create a deck.aistack.codes workspace and start the Smart Deck intake workflow for brand-aware deck transformation.',
    canonicalPath: '/auth/sign-up'
  },
  '/sign_in_landing': {
    title: 'Smart Deck Intake',
    description:
      'Create Smart Deck intake by adding the source material and AI provider access needed before entering the workspace.',
    canonicalPath: '/sign_in_landing',
    noindex: true
  },
  '/auth/callback': {
    title: 'Completing Sign-In',
    description: 'Validating the sign-in response and preparing your deck.aistack.codes session.',
    canonicalPath: '/auth/callback',
    noindex: true
  },
  '/auth/success': {
    title: 'Sign-In Success',
    description: 'Preparing your deck.aistack.codes workspace after sign-in.',
    canonicalPath: '/auth/success',
    noindex: true
  }
};

export const publicBreadcrumbs: Record<string, BreadcrumbItem[]> = {
  '/about': [
    { label: 'Home', href: '/' },
    { label: 'About', href: '/about' }
  ],
  '/pricing': [
    { label: 'Home', href: '/' },
    { label: 'Pricing', href: '/pricing' }
  ],
  '/contact': [
    { label: 'Home', href: '/' },
    { label: 'Contact', href: '/contact' }
  ],
  '/privacy': [
    { label: 'Home', href: '/' },
    { label: 'Privacy', href: '/privacy' }
  ],
  '/terms': [
    { label: 'Home', href: '/' },
    { label: 'Terms', href: '/terms' }
  ],
  '/vcs': [
    { label: 'Home', href: '/' },
    { label: 'For VCs', href: '/vcs' }
  ],
  '/billing': [
    { label: 'Home', href: '/' },
    { label: 'Billing', href: '/billing' }
  ]
};
