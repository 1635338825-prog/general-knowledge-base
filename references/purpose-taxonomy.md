# Purpose Taxonomy

`role_for_purpose` is now an internal classification field. It can stay in cache or digest, but it is not a visible page section.

## Generic Roles

- `direct-evidence`: same policy, object, outcome, or question as the vault goal
- `mechanism-evidence`: explains channels, mechanisms, intermediate variables, or transmission paths
- `method-support`: supports identification, estimation, measurement, validation, or workflow
- `bridge-literature`: connects two important parts of the active thesis line that are not yet well linked
- `writing-support`: mainly helps structure sections, chapter language, or argument flow
- `background`: explains context, policy setting, history, or literature landscape
- `concept`: defines an important concept, variable, or interpretation frame
- `counterpoint`: provides contrary evidence, limitations, or scope boundaries
- `other`: useful but not yet clearly classified

## Current Thesis Defaults

For the thesis on national big data comprehensive pilot zones and enterprise resource allocation efficiency:

- direct evidence: same policy plus resource misallocation or enterprise efficiency outcomes
- mechanism evidence: digital transformation, data assetization, innovation, financing constraints, information environment, human capital
- concept support: resource misallocation, capital/labor allocation, TFP, information friction
- method support: multi-period DID, staggered adoption, event study, IPW-DID, TWFE bias

## Rule

Always classify relative to the active `purpose`, not the document title.

The classification is mainly useful for:

- digest metadata
- grouping
- rebuild
- later aggregation logic

In thesis mode, these roles should also inform how working pages under `wiki/core/`, `wiki/literature/`, `wiki/identification/`, and `wiki/drafts/` are prioritized.

It is not a license to inject a visible "this serves the current thesis by..." section into every source page.
