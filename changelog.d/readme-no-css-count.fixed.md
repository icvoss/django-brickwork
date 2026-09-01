- **README's composition claim states the measured figure.** It said 47 of the
  examples add no CSS, which contradicted `docs/POSITIONING.md`'s "50 of the 51"
  and was internally incoherent: it named a single exception while leaving three
  files unaccounted for. Measured against the shipped tree, exactly one example
  carries a `<style>` block (`examples/app/date-range-picker.html`), so 50 of the
  51 files add none. POSITIONING was right and README was wrong; both now agree.
