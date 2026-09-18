- **Derived attribute-position classifier gate** (icvoss/django-brickwork#390,
  ADR-097). A test-time scan re-derives every `attr="{{ ... }}"` under
  `src/brickwork/templates/brickwork/`, classifies each hit as composed,
  extends-unreachable, or known-exempt, and pins the residue to a checked-in
  inventory that cannot grow or shrink silently. Seam-covered `bw_attr` /
  `bw_data_attrs` sites and author-literal if/elif class modifiers are
  validated by absence. Does not migrate residual sites; #390 stays open.
