# MARINA Motion Engine · Implementation and gates

Centralized values: `src/theme/tokens.ts#motion`; shared helpers: `src/theme/motion.ts`. No additional native animation package is required.

| Motion | Design time | Trigger | Exit/fallback |
|---|---:|---|---|
| Press feedback | 125 ms target | press in/out | disabled / Reduce Motion => no scale |
| Bottom-tab focus | 220 ms target | selected tab | static highlight currently; transition beyond highlight is **NOT IMPLEMENTED** |
| Card entrance | 320 ms | mount | max 6*55ms stagger; Reduce Motion => static |
| Modal open | 340 ms target | navigate | existing Router transition, exact device timing not measured |
| Chart/progress reveal | 700 ms | data update | static percentage with Reduce Motion |
| Loading shimmer | 650+650 ms | while loading in foreground | stops on unmount/background/reduced-motion |
| AI orbital ring | 1700 ms loop | server request in progress | stops on done/error/offline/reduced-motion/background |

The static chart has no fabricated series. The assistant UI enters `processing` only while a real authenticated server request is pending. Bright flashing, fake speaking/listening states and forever-looping decorative animation are prohibited.

**Required device QA before release:** Android and iOS frame timing and jank with realistic queues/rooms, memory profiles, battery, screen-reader accessibility, small and large font, app background/resume, gesture interruption. None of those measurements is implied by successful Jest/CI.
