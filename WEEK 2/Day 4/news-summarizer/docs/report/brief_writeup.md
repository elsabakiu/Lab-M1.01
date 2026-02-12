# Project Brief Write-up

One of the biggest challenges in this project was dealing with mismatches between expected and actual data shapes across modules. The summarizer initially treated articles as dictionaries, while the News API client returned `NewsArticle` dataclass objects. This caused runtime errors like `'NewsArticle' object is not subscriptable`. Another challenge was test reliability: some tests patched incorrect import paths and depended on local environment variables, which made failures confusing and environment-specific.

I solved these issues by tracing data flow end-to-end and aligning the interfaces. In the summarizer layer, I added safe field access that supports both dict-style and object-style inputs. In tests, I corrected patch targets to the actual import locations used by the code under test and updated assertions to match dataclass attributes. I also reduced environment coupling by injecting a test API key where needed, so tests focus on behavior rather than setup.

The biggest learning was how important it is to keep contracts explicit between components. Small assumptions (for example, “this is always a dict”) can break quickly as the codebase evolves. I also learned that stable unit tests require patching where symbols are *used*, not where they originally came from.

For improvement, I would add stricter typing across service boundaries, introduce validation tests for data contracts, and remove unused imports to keep modules clean. I would also add CI checks for formatting, linting, and test execution so regressions are caught early.
