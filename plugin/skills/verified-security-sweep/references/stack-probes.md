# Quick probes per stack

Contents: Node / Express / pg; Python / Django / DRF; Ruby / Rails; Go / net/http / database/sql; Java / Spring; C# / ASP.NET Core / EF Core; Rust / axum or actix / sqlx; PHP / Laravel; Infrastructure (any stack); Frontend (React or similar).

Probes are greps that point at places to read. A hit is not a finding; a probe that returns
nothing is not a clean bill. They exist to orient the first ten minutes of a sweep, and to be
replaced by the project's own guards as soon as a class recurs.

Derive new probes from the project's rules file: every sentence of the form "X always does Y"
is a probe (`grep` for X, read the hits that do not do Y).

Placeholders in angle brackets (`<auditHelper>`, `<tenantIdField>`) stand for the project's own
names; replace them before running.

## Node / Express / pg

```bash
# SQL interpolation carrying a value (structure-only interpolation is fine; read each hit)
grep -rn 'query.*`.*\${' src/ --include=*.ts | grep -v '\$[0-9]'

# JWT verification without a pinned algorithm
grep -rn "jwt\.verify" src/ --include=*.ts | grep -v "algorithms"

# Handlers with mutations and no audit call
for f in src/controllers/*.ts; do
  m=$(grep -cE "UPDATE |DELETE FROM |INSERT INTO " "$f"); a=$(grep -c "<auditHelper>" "$f")
  [ "$m" -gt 0 ] && [ "$a" = "0" ] && echo "AUDIT GAP: $f ($m mutations)"
done

# Tenant key taken from the request instead of the session
grep -rn "req\.body\.<tenantIdField>\|req\.params\.<tenantIdField>" src/controllers/

# Routes mounted without the auth middleware (read the list; public ones are expected)
grep -rn "router\.\(get\|post\|put\|patch\|delete\)" src/routes/ | grep -v "authenticate"

# Check next to a lock (the check reads the pre-wait snapshot)
grep -rn -B2 -A2 "FOR UPDATE\|FOR SHARE" src/ | grep -i "count(\|exists"

# UTC day used for a date with meaning
grep -rn "toISOString()\.slice(0, *10)\|toISOString()\.split('T')" src/

# Fire-and-forget with a swallowed error
grep -rn "\.catch(() => {})" src/

# Body parsers mounted globally (what formats does every route accept?)
grep -rn "express\.\(json\|urlencoded\|raw\|text\)" src/index.ts src/app.ts 2>/dev/null
```

## Python / Django / DRF

```bash
# Raw SQL with formatting
grep -rn "\.raw(\|cursor\.execute(" --include=*.py . | grep -E "%|\.format\(|f\""

# Querysets without the tenant filter in views that take a pk
grep -rn "get_object_or_404\|\.objects\.get(" --include=*.py apps/ | grep -v "organization"

# Views without permission classes
grep -rn "class .*APIView\|class .*ViewSet" --include=*.py . | while read l; do
  f=${l%%:*}; grep -q "permission_classes" "$f" || echo "NO PERMISSION CLASSES: $f"; done

# Naive datetimes
grep -rn "datetime\.now()\|date\.today()" --include=*.py . | grep -v "timezone"
```

## Ruby / Rails

```bash
grep -rn "where(\"" app/ | grep "#{"
grep -rn "find(params" app/controllers/ | grep -v "current_"
grep -rn "skip_before_action :authenticate" app/
grep -rn "Date\.today\|Time\.now" app/ lib/ | grep -v "zone"
```

## Go / net/http / database/sql

```bash
grep -rn "fmt\.Sprintf(.*SELECT\|fmt\.Sprintf(.*UPDATE\|+ \"" --include=*.go . | grep -i "select\|update\|delete"
grep -rn "r\.URL\.Query()\.Get(\"org\|mux\.Vars(r)\[\"org" --include=*.go .
grep -rn "time\.Now()\.Format(\"2006-01-02\")" --include=*.go .
```

## Java / Spring

```bash
# SQL or JPQL built with concatenation or formatting (parameters are ? or :name)
grep -rn "createQuery(\|createNativeQuery(\|jdbcTemplate\.\(query\|update\)" --include=*.java src/main | grep -E '\+ *"|String\.format|\.formatted\('

# Endpoints without a method-level authorization annotation (read the class: a class-level one covers them)
grep -rln "@\(Get\|Post\|Put\|Patch\|Delete\|Request\)Mapping" --include=*.java src/main | while read f; do
  grep -q "@PreAuthorize\|@Secured\|@RolesAllowed" "$f" || echo "NO METHOD AUTHZ: $f"; done

# Lookups by id from the path with no owner or tenant in the query
grep -rn "findById(\|getReferenceById(" --include=*.java src/main | grep -v -i "tenant\|owner\|principal"

# Security config that opens everything, or disables CSRF, or permits all
grep -rn "permitAll()\|csrf()\.disable()\|csrf(AbstractHttpConfigurer::disable)" --include=*.java src/main

# Request objects bound straight into entities (mass assignment)
grep -rn "@RequestBody .*Entity\|@ModelAttribute" --include=*.java src/main

# Deserialization of untrusted input with type information
grep -rn "enableDefaultTyping\|@JsonTypeInfo\|ObjectInputStream" --include=*.java src/main

# Dates without a zone
grep -rn "LocalDate\.now()\|LocalDateTime\.now()" --include=*.java src/main | grep -v "ZoneId\|ZoneOffset\|Clock"
```

## C# / ASP.NET Core / EF Core

```bash
# Raw SQL with interpolation ({0} parameters and FromSqlInterpolated are fine; read each hit)
grep -rn "FromSqlRaw(\|ExecuteSqlRaw(" --include=*.cs . | grep -E '\$"|\+ *"|string\.Format'

# Controllers or actions without [Authorize] (read the list; [AllowAnonymous] is expected on public ones)
grep -rln "\[ApiController\]\|: Controller\b\|: ControllerBase" --include=*.cs . | while read f; do
  grep -q "\[Authorize" "$f" || echo "NO AUTHORIZE: $f"; done
grep -rn "\[AllowAnonymous\]" --include=*.cs .

# Lookups by id from the route with no owner or tenant in the query
grep -rn "FindAsync(\|FirstOrDefaultAsync(\|SingleOrDefaultAsync(" --include=*.cs . | grep -v -i "tenant\|owner\|userid"

# Entities bound straight from the request (mass assignment; look for [Bind] or a DTO)
grep -rn "\[FromBody\] *[A-Z][A-Za-z]*Entity\|\[FromForm\] *[A-Z][A-Za-z]*Entity" --include=*.cs .

# Anti-forgery turned off on state-changing endpoints
grep -rn "\[IgnoreAntiforgeryToken\]\|ValidateAntiForgeryToken" --include=*.cs .

# Binary or polymorphic deserialization of untrusted input
grep -rn "BinaryFormatter\|TypeNameHandling\.\(All\|Auto\|Objects\)" --include=*.cs .

# Local time where a date has meaning
grep -rn "DateTime\.Now\b\|DateTime\.Today\b" --include=*.cs . | grep -v "UtcNow"
```

## Rust / axum or actix / sqlx

```bash
# Queries built from strings (sqlx::query!, query_as! and bound parameters are fine; read each hit)
grep -rn "sqlx::query(\|query_as::<\|\.execute(&" --include=*.rs src/ | grep -E 'format!|\+ *"|push_str'

# Handlers that take an id from the path with no owner or tenant in the query
grep -rn "Path<" --include=*.rs src/ | grep -v -i "tenant\|owner\|claims\|user_id"

# Routes without an auth layer or extractor (read the router: a layer on the parent covers them)
grep -rn "\.route(\|web::resource(\|web::scope(" --include=*.rs src/ | grep -v -i "auth\|require\|claims"

# unwrap and expect on request-controlled values (a panic is a denial of service on one request)
grep -rn "\.unwrap()\|\.expect(" --include=*.rs src/ | grep -i "header\|query\|json\|param\|body"

# Unsafe blocks and raw deserialization of untrusted input
grep -rn "unsafe {" --include=*.rs src/
grep -rn "from_str::<\|serde_json::from_slice" --include=*.rs src/ | grep -v "Deserialize"

# Local time where a date has meaning
grep -rn "Local::now()\|Local::today()" --include=*.rs src/
```

## PHP / Laravel

```bash
# Raw queries with interpolation (bindings as ? or :name are fine; read each hit)
grep -rn "DB::raw(\|DB::select(\|DB::statement(\|whereRaw(\|orderByRaw(\|selectRaw(" --include=*.php app/ | grep -E '\$[a-zA-Z_]+|\. *"'

# Route groups and routes without an auth middleware (read the list; public ones are expected)
grep -rn "Route::\(get\|post\|put\|patch\|delete\|resource\|apiResource\)" routes/ | grep -v "auth\|sanctum\|middleware"

# Model lookups by request id with no owner or tenant scope
grep -rn "::find(\$\|::findOrFail(\$\|::where('id'" --include=*.php app/ | grep -v -i "user()\|tenant\|owner"

# Mass assignment: unguarded models, or create/update fed the whole request
grep -rn "\$guarded *= *\[\]\|::unguard()" --include=*.php app/
grep -rn "::create(\$request->all())\|->update(\$request->all())\|->fill(\$request->all())" --include=*.php app/

# Unescaped output in templates
grep -rn "{!!" resources/views/

# Unserialize of untrusted input
grep -rn "unserialize(" --include=*.php app/

# Local time where a date has meaning (the app timezone applies; read config/app.php)
grep -rn "now()->toDateString()\|Carbon::today()\|date('Y-m-d')" --include=*.php app/
```

## Infrastructure (any stack)

```bash
# Actions not pinned to a SHA
grep -rn "uses:" .github/workflows/ | grep -v "@[0-9a-f]\{40\}"

# Secrets at workflow level (exposed to every step)
awk '/^env:/{f=1} f&&/secrets\./{print FILENAME": "$0} /^jobs:/{f=0}' .github/workflows/*.yml

# Event data interpolated into run: (script injection)
grep -rn '\${{ *github\.event\.\(pull_request\.\(title\|body\)\|head_commit\.message\|comment\.body\)' .github/workflows/

# Upload that runs even when a cleanup step failed
grep -rn -B3 "upload-artifact" .github/workflows/ | grep "if: always()"

# Compose hardening
for k in cap_drop no-new-privileges read_only; do grep -q "$k" docker-compose*.yml || echo "MISSING: $k"; done

# Case-insensitive flag on a regex that verifies a signature or an identity
grep -rn "(?i)" deploy*.sh .github/workflows/ 2>/dev/null | grep -i "identity\|issuer\|refs/"
```

## Frontend (React or similar)

```bash
grep -rn "dangerouslySetInnerHTML\|innerHTML\|document\.write" src/
grep -rn "window\.location\.href\|navigate(" src/ | grep -i "param\|query\|search"
grep -rn "localStorage\.setItem\|sessionStorage\.setItem" src/
grep -rn "target=\"_blank\"" src/ | grep -v "noopener"
# Error reporters that ship the full URL (tokens in path or query)
grep -rn "location\.href" src/ | grep -i "report\|sentry\|fetch"
```
