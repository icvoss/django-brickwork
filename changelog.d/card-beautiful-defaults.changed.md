- **Default card reads on a white canvas without kwargs.** The zero-kwargs
  `.bw-card` keeps hairline, radius-lg and elevation-1, replaces the
  light-theme paper sheen (invisible on white fill) with a soft ambient under
  the elevation token, and slightly strengthens the edge so the card does not
  dissolve into a white page. Title type keeps heading-md with optional
  tracking and balanced wrap; body text uses `pretty` wrap. Dark theme still
  uses the plain elevation ramp.
