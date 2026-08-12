# Feature Specification: Product Catalog

**Feature Branch**: `001-product-catalog`

**Created**: 2026-08-11

**Updated**: 2026-08-11 — source conversation supplied; data model corrected

**Status**: Draft

**Input**: User description: "Add a new section for product catalog, should have information following data from this chat https://claude.ai/share/411e1a6e-a3c5-4e28-8f86-0c1e304ad0dc the images should come from an storage outsider and saved as url on our database"

> **Source note**: The shared link was unreachable, but its content was supplied directly. The
> product attributes, validation rules, and scope below are taken from that source rather than
> inferred. The earlier draft of this spec guessed at a specialty-coffee model (origin, roast
> level, varietal, altitude, tasting notes, categories, multiple images); the source defines a
> deliberately simpler MVP product, and this revision replaces the guess entirely.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse the product catalog (Priority: P1)

A visitor requests the catalog and receives the products currently on sale — each with its name,
description, price, stock, and image — newest first. Products that have been deactivated are
absent. Selecting a single product returns that product's full detail.

**Why this priority**: This is the catalog. It is the first point at which the system returns real
product data to a caller, and it stands alone as a shippable slice: a read-only storefront feed.

**Independent Test**: Seed two or three products, request the catalog, and confirm the response
carries every active product with all of its attributes; deactivate one and confirm it disappears.
Requires no authentication, no maintenance flows, and no write path.

**Acceptance Scenarios**:

1. **Given** several active products exist, **When** a visitor requests the catalog, **Then** all
   active products are returned, each with its identifier, name, description, price, stock, image
   address, and active state.
2. **Given** a mix of active and inactive products, **When** a visitor requests the catalog,
   **Then** only the active products are returned.
3. **Given** products created at different times, **When** a visitor requests the catalog,
   **Then** they are ordered most recently created first.
4. **Given** an active product, **When** a visitor requests it by its identifier, **Then** that
   single product is returned with the same attributes as in the listing.
5. **Given** a product with no image address recorded, **When** it is listed or retrieved,
   **Then** it is returned normally with an empty image address rather than being omitted or
   failing.
6. **Given** an empty catalog, **When** a visitor requests it, **Then** an empty list is returned
   rather than an error.

---

### User Story 2 - Reject invalid product data (Priority: P2)

Someone submitting a product gets it checked before it is stored. A price of zero or below is
refused with a message saying so. A missing name, a malformed image address, or a negative stock
is refused. Nothing invalid reaches the database.

**Why this priority**: Validation is what separates an API from a hole in the database. It is
called out in the source as something to be demonstrated live. It depends on Story 1's data shape
but is independently testable and independently valuable.

**Independent Test**: Submit a product with a price of `0`, then `-5`, then a valid price, and
confirm the first two are refused with a field-level message and the third is accepted.

**Acceptance Scenarios**:

1. **Given** a product submission with a price of zero, **When** it is submitted, **Then** it is
   refused with a message stating the price must be greater than zero, and nothing is stored.
2. **Given** a product submission with a negative price, **When** it is submitted, **Then** it is
   refused with the same message.
3. **Given** a product submission with no name, **When** it is submitted, **Then** it is refused
   identifying the name as required.
4. **Given** a product submission whose image address is not a well-formed address, **When** it is
   submitted, **Then** it is refused identifying the image address as invalid.
5. **Given** a product submission with a negative stock, **When** it is submitted, **Then** it is
   refused; a stock value can never be below zero.
6. **Given** a price with more than two decimal places or more than eight whole digits,
   **When** it is submitted, **Then** it is refused as outside the permitted range.
7. **Given** a valid product submission, **When** it is submitted, **Then** it is stored and
   returned with its newly assigned identifier and creation time.

---

### User Story 3 - Maintain the catalog (Priority: P3)

A staff member creates products, corrects a price or a stock figure, records an image address, and
deactivates a product that is no longer sold — without deleting it. Common corrections are
possible directly from a list view without opening each product.

**Why this priority**: Necessary for the catalog to stay accurate, but the first products can be
seeded, so this does not block Stories 1 and 2 from shipping.

**Independent Test**: Create a product through the maintenance interface, edit its price and stock
from the list, deactivate it, and confirm it vanishes from the visitor-facing catalog while its
record remains.

**Acceptance Scenarios**:

1. **Given** a staff member on the maintenance interface, **When** they view the product list,
   **Then** each product's name, price, stock, and active state are shown.
2. **Given** the product list, **When** a staff member edits a price, a stock, or an active state
   directly in that list and saves, **Then** the change is persisted without opening the product.
3. **Given** many products, **When** a staff member searches by part of a product name,
   **Then** matching products are shown.
4. **Given** a product that is no longer sold, **When** a staff member marks it inactive,
   **Then** it disappears from the visitor-facing catalog and its record is retained.
5. **Given** a product referenced anywhere in the maintenance interface, **When** it is displayed,
   **Then** it is identified by its name rather than by an opaque object label.
6. **Given** an existing product, **When** a staff member updates it or removes it,
   **Then** the change is reflected in the visitor-facing catalog on the next request.

---

### Edge Cases

- A price is submitted as exactly zero — refused, per the source's rule of "greater than zero",
  which is stricter than merely rejecting negatives.
- A price is submitted with more precision than two decimal places, or above 99,999,999.99.
- A monetary value is subjected to arithmetic that could introduce rounding drift — prices must be
  held and compared exactly, never as approximate binary values.
- A stock value is submitted as negative — refused at the storage layer itself, not only at the
  edge, so no path can write one.
- An image address points at a host that is unreachable or has deleted the file — the catalog must
  still return the product; it does not verify that the address resolves.
- An image address is well-formed but points somewhere other than the intended image store.
- A product is submitted with no description or no image address — both are optional and must be
  accepted as empty.
- A product name longer than 200 characters.
- A visitor requests a product that is inactive, or one that never existed — both must be
  indistinguishable, returning a plain "not found".
- The catalog is empty.
- Two staff members edit the same product simultaneously.
- A product is deleted outright rather than deactivated — the interface permits it, but it
  destroys history; deactivation is the intended path.

## Requirements *(mandatory)*

### Functional Requirements

**Product data**

- **FR-001**: System MUST store products, each carrying a name, a description, a price, a stock
  figure, an image address, an active flag, and a creation timestamp.
- **FR-002**: System MUST require a name of at most 200 characters.
- **FR-003**: System MUST treat the description as optional, defaulting to empty.
- **FR-004**: System MUST hold prices as exact decimal values with two decimal places, supporting
  values up to 99,999,999.99. Prices MUST NOT be held as approximate values, because binary
  floating point cannot represent common monetary amounts exactly and the resulting drift shows up
  as money appearing or disappearing.
- **FR-005**: System MUST reject any price that is not greater than zero, and MUST state that the
  price must be greater than zero when doing so.
- **FR-006**: System MUST hold stock as a whole number that cannot be negative, enforced by the
  storage layer itself so that no code path can record a negative stock. Default is zero.
- **FR-007**: System MUST treat the image address as optional, defaulting to empty.
- **FR-008**: System MUST record whether a product is active, defaulting to active.
- **FR-009**: System MUST record when each product was created, set automatically and not
  supplied by the caller.
- **FR-010**: System MUST identify a product by its name wherever it is displayed in an
  administrative context.

**Images**

- **FR-011**: System MUST store product images as addresses pointing at an external image store.
  The system MUST NOT accept, store, resize, optimize, or serve image binary data — file upload
  and image processing are explicitly out of scope for this iteration.
- **FR-012**: System MUST validate that a supplied image address is a well-formed address at the
  moment it is submitted, and MUST refuse a malformed one.
- **FR-013**: System MUST return a product whose image address cannot be loaded by the caller
  without failing the surrounding listing or detail response. The system does not verify that an
  address resolves.

**Browsing**

- **FR-014**: Callers MUST be able to list products and to retrieve a single product by its
  identifier.
- **FR-015**: System MUST exclude inactive products from the visitor-facing catalog, in both
  listing and single-product retrieval.
- **FR-016**: System MUST order the catalog listing by creation time, most recent first.
- **FR-017**: System MUST return an empty list, not an error, when no products match.
- **FR-018**: System MUST return each product's identifier, name, description, price, stock,
  image address, and active state, and MUST NOT expose any attribute beyond these.

**Maintenance**

- **FR-019**: Callers MUST be able to create, update, and delete products.
- **FR-020**: System MUST validate every submission against FR-002 through FR-007 before storing
  it, and MUST report which field failed and why.
- **FR-021**: Staff MUST be able to maintain products through an administrative interface that
  lists each product's name, price, stock, and active state.
- **FR-022**: Staff MUST be able to change a product's price, stock, and active state directly
  from that list, without opening each product individually.
- **FR-023**: Staff MUST be able to find products by searching part of a product name.
- **FR-024**: System MUST allow a product to be withdrawn from sale by deactivating it, retaining
  its record, rather than requiring deletion.

**Deferred access control (see the security note below)**

- **FR-025**: System MUST, before this feature is exposed outside a local development machine,
  restrict product creation, update, and deletion to administrators, and restrict all other
  callers to reading. Until then, the catalog's write operations are deliberately unprotected and
  the feature MUST NOT be deployed.

### Key Entities *(include if feature involves data)*

- **Product**: A single item offered for sale. Carries a name (≤200 characters), an optional
  description, an exact decimal price greater than zero, a non-negative stock count, an optional
  address of an externally hosted image, an active flag, and a creation timestamp. It has no
  sub-entities in this iteration: no categories, no variants, no additional images.

The catalog is the first of several planned business areas; orders and customer accounts are
separate domains and are not part of this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A caller requesting the catalog receives every active product with all seven of its
  attributes, and zero inactive products, verified across listing and single-product retrieval.
- **SC-002**: 100% of submissions with a price of zero or below are refused with a message naming
  the price, and none of them are stored.
- **SC-003**: 100% of submissions with a negative stock, a missing name, or a malformed image
  address are refused before storage.
- **SC-004**: Monetary values survive a store-and-retrieve round trip with zero loss of precision,
  verified against amounts that binary floating point cannot represent exactly.
- **SC-005**: The catalog listing and single-product retrieval respond within 2 seconds for a
  catalog of up to 500 products.
- **SC-006**: A staff member can create a complete product, including its image address, and have
  it appear in the catalog in under 3 minutes without assistance.
- **SC-007**: A staff member can correct a price or stock figure from the product list in under 15
  seconds.
- **SC-008**: The system holds zero image binary data; 100% of stored image references are
  addresses pointing outside the system.
- **SC-009**: Deactivating a product removes it from the visitor-facing catalog on the next
  request while its record remains retrievable administratively, in 100% of cases.
- **SC-010**: The database schema can be built from nothing to its current state in a single
  reproducible run, on a clean machine, with no manual steps.

## Assumptions

**About scope**

- This feature covers the catalog only. Carts, checkout, orders, payment, and customer accounts
  are separate domains, out of scope here.
- Stock is a plain figure carried on the product. Reserving, decrementing, and overselling
  protection belong to checkout and are out of scope; the non-negative constraint here is a schema
  guarantee, not an inventory system.
- Product variants — the same product in several sizes or grinds at different prices — are out of
  scope. One price per product. *(Resolves the earlier Q3.)*
- Categories, product tagging, reviews, ratings, wishlists, and recommendations are out of scope.
- Public filtering and public text search are out of scope. Name search exists only in the
  administrative interface. The visitor-facing catalog is an ordered list of active products.
- The catalog is presented in a single language and a single currency.

**About images**

- An external image store already exists or is provisioned separately; standing it up is not part
  of this feature.
- Images are placed in that store out of band. This system only records the resulting address.
- Recorded addresses are durable and publicly readable; the system does not mint time-limited
  access links, and does not check that an address still resolves.
- The model records no alternative text for images. This is a known accessibility gap carried over
  from the source: without alt text, catalog images are opaque to screen readers. Recommended for
  a later iteration rather than added here, to keep this spec faithful to the agreed model.
- No allowlist of permitted image hosts is imposed in this iteration, so any well-formed address is
  accepted. Worth revisiting once the write path is protected under FR-025.

**About users and access**

- Two audiences: visitors, who read the catalog, and staff, who maintain it.
- Staff maintenance runs through an administrative interface, which handles authentication itself.
  *(Partially resolves the earlier Q2.)*
- The catalog's write operations over the API carry no access control in this iteration. This is a
  deliberate, recorded decision to keep the validation behaviour of Story 2 demonstrable on a local
  machine — not an oversight. FR-025 governs closing it.

**About the environment**

- The catalog holds on the order of hundreds of products.
- The schema is built through versioned, ordered migration files committed alongside the code, so
  that any clone reproduces the same database. Generating a migration and applying it are separate
  steps, which is what makes the schema reviewable before it touches a database.

## Security Note — unprotected write path

The source explicitly flags this and it is reproduced here so it cannot be lost between the
specification and the implementation.

As specified, product creation, update, and deletion are reachable by any caller, with no
authentication and no authorization. Anyone who can reach the API can alter prices, change stock
figures, or delete the catalog outright.

This is acceptable **only** on a local development machine, and only while the validation behaviour
in Story 2 is being demonstrated. FR-025 requires that read access be separated from write access,
with writes restricted to administrators, before this feature reaches any shared or public
environment. Treat FR-025 as a release blocker, not a follow-up improvement.

## Resolved Clarifications

- **Q1 — Catalog attributes.** Resolved. The source defines a deliberately minimal MVP product:
  name, description, price, stock, image address, active flag, creation time. The earlier
  specialty-coffee guess (origin, roast level, process, varietal, altitude, tasting notes,
  categories, multiple ordered images with alt text) is withdrawn in full.
- **Q2 — Catalog maintenance and access.** Partially resolved. Maintenance runs through an
  administrative interface, and the API additionally exposes unprotected write operations as
  deliberate, temporary debt. The permanent access-control design is deferred to a later
  authentication feature and captured as FR-025.
- **Q3 — Product variants.** Resolved: one price per product; no variants.
