- **Example sections: the copy-paste unit is now a band, not a whole page.**
  Thirteen section variants ship under `examples/sections/<type>/<variant>.html`
  across four types (hero, features, cta, content). Previously every example was
  a complete page, so a consumer who wanted a pricing band had to copy a pricing
  page and delete most of it. Sections are package data off the template-loader
  path exactly as the page examples are (ADR-056), and each carries its copy
  inline, so all but one render from an empty context.
- **A long-form prose floor, `bw-prose`.** One class on a wrapper styles bare
  `h1` to `h6`, paragraphs, lists, blockquotes, inline code, code blocks,
  tables, figures and rules, at the 65ch reading measure, entirely from the
  existing text-role and colour tokens. It is the shape a rendered Markdown body
  or a CMS rich-text field actually arrives in: no classes on any child. Every
  descendant rule sits inside `:where()`, so a consumer's own class on any
  element wins without `!important`. Both themes are covered by the token layer
  rather than by theme-specific rules.
