---
name: JusticeCongo AI Design System
colors:
  surface: '#f8f9ff'
  surface-dim: '#d1dbec'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eef4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dfe9fa'
  surface-container-highest: '#d9e3f4'
  on-surface: '#121c28'
  on-surface-variant: '#45464c'
  inverse-surface: '#27313e'
  inverse-on-surface: '#eaf1ff'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#575e70'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#141b2b'
  on-primary-container: '#7d8497'
  inverse-primary: '#c0c6db'
  secondary: '#295dab'
  on-secondary: '#ffffff'
  secondary-container: '#7dabfe'
  on-secondary-container: '#003e82'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#281900'
  on-tertiary-container: '#ae7a0e'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce2f7'
  primary-fixed-dim: '#c0c6db'
  on-primary-fixed: '#141b2b'
  on-primary-fixed-variant: '#404758'
  secondary-fixed: '#d7e2ff'
  secondary-fixed-dim: '#abc7ff'
  on-secondary-fixed: '#001b3f'
  on-secondary-fixed-variant: '#004590'
  tertiary-fixed: '#ffdeac'
  tertiary-fixed-dim: '#f9bc51'
  on-tertiary-fixed: '#281900'
  on-tertiary-fixed-variant: '#604100'
  background: '#f8f9ff'
  on-background: '#121c28'
  surface-variant: '#d9e3f4'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  citation-code:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 16px
  md: 24px
  lg: 32px
  xl: 48px
  sidebar-width: 280px
  max-content-width: 1200px
---

## Brand & Style
The design system is engineered to provide a sense of clarity, authority, and accessibility for citizens navigating the complexities of Congolese law. It balances the gravity of legal aid with a modern, high-tech interface that feels approachable rather than bureaucratic.

The aesthetic follows a **Modern / Professional** style with strong influences from **Minimalism** and **Tactile** design. Key characteristics include:
- **Spaciousness:** Generous padding and wide margins to reduce cognitive load during legal research.
- **Modernity:** A clean, systematic approach that utilizes subtle depth to organize complex information.
- **Trustworthiness:** A palette and layout that feel established and official, yet forward-thinking.

## Colors
The palette is rooted in institutional stability with functional accents representing the Democratic Republic of the Congo.

- **Primary (#111827):** Used for core branding, primary actions, and high-contrast text. It provides a grounded, authoritative feel.
- **Secondary (#2B5FAD):** The "DRC Blue," reserved for active states, links, and interactive UI cues. It signals action and navigation.
- **Tertiary (#C9922A):** The "DRC Gold," specifically designated for AI-generated signatures, legal citations, and verified badges.
- **Neutrals:** A tiered grey scale is used to manage information hierarchy, with `#4B5563` acting as the standard for secondary body text and metadata.
- **Surface Strategy:** Use `#F4F5F7` for the navigation sidebar to create a distinct structural break from the main `#FAFAFC` content area.

## Typography
The system employs a dual-font strategy to distinguish between conversational UI and formal legal references.

- **Inter:** The primary workhorse. It is used for all interface elements, chat bubbles, and navigation to ensure maximum legibility and a contemporary feel.
- **JetBrains Mono:** Utilized exclusively for legal citations, article numbers (e.g., *Article 15*), and technical metadata. This monospaced font provides a visual "anchor" that differentiates law from conversation.
- **Scaling:** On mobile devices, `display-lg` should scale down to `headline-lg` to maintain readability without overwhelming the viewport.

## Layout & Spacing
The layout follows a **Fixed Grid** approach for the sidebar and a **Fluid** approach for the chat container to maximize readability on various screen sizes.

- **Grid System:** A 12-column grid is used for desktop views. The chat interface is centered within the main area, typically spanning 8 columns to prevent line lengths from becoming too long for legal text.
- **Rhythm:** A 4px baseline grid ensures vertical consistency.
- **Breakpoints:**
  - **Desktop (1280px+):** Full sidebar (280px) + Fluid content area.
  - **Tablet (768px - 1279px):** Collapsed sidebar (icon only) + Full-width content area.
  - **Mobile (<768px):** Hidden sidebar (hamburger menu) + Full-width content with reduced horizontal margins (16px).

## Elevation & Depth
This design system uses depth to indicate interactivity and focus. The strategy relies on **Ambient Shadows** and **Tonal Layers**.

- **Chat Input:** Uses the highest elevation. A soft, extra-diffused shadow (Blur: 20px, Y: 8px, Opacity: 6% Black) makes the floating input feel reachable.
- **Cards and Bubbles:** Use a "Low-contrast outline" combined with a very subtle shadow (Blur: 4px, Y: 2px, Opacity: 4% Black) to sit just above the background surface.
- **Sidebar:** Flat depth, differentiated solely by its `#F4F5F7` background color, ensuring it remains secondary to the main action area.

## Shapes
The shape language is "Rounded," conveying a friendly and modern personality.

- **Standard Elements:** Buttons, chips, and small input fields use a `0.5rem` (8px) radius.
- **Large Containers:** Chat bubbles and the main floating input container use a `1.5rem` (24px) radius to emphasize the "Cortex-inspired" spaciousness.
- **Sidebar Icons:** Use a `0.75rem` (12px) radius for hover states and active indicators.

## Components

### Chat Bubbles
- **User Bubble:** Minimalist with a light grey border (`#E5E7EB`) and no background. Text is aligned right.
- **AI Bubble:** Solid background using `#FAFAFC` or white, with a soft shadow. Use the "DRC Gold" for AI-specific iconography or citations within the bubble.

### Primary Input
- **Style:** A large, floating text area with a `24px` corner radius.
- **Shadow:** Highly diffused ambient shadow.
- **Icons:** Use Lucide icons (size 20px) for attachments and send actions, tinted with the Primary color.

### Sidebar Navigation
- **Active State:** A subtle `#2B5FAD` (DRC Blue) vertical bar on the left or a soft blue background tint with a 12px corner radius.
- **Icons:** Lucide icons in `20px`, using `#4B5563` for inactive and `#2B5FAD` for active states.

### Legal Citations (Chips)
- **Style:** Small, pill-shaped chips using `JetBrains Mono`.
- **Color:** Background in a very light tint of `#C9922A` (Gold) with dark gold text for high visibility.

### Buttons
- **Primary:** Solid `#111827` with white text. 16px vertical padding, 24px horizontal.
- **Secondary:** Transparent background with a `#111827` border and text.