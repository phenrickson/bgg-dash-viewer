# BGG-Dash-Viewer Migration Plan
## Migrate from gcp-demos-411520 to bgg-data-warehouse

### Overview
This plan outlines the migration of bgg-dash-viewer from the legacy `gcp-demos-411520` GCP project to the new `bgg-data-warehouse` project with its reorganized dataset structure.

### Current State
- **Project ID**: gcp-demos-411520
- **Dataset Structure**: Environment-specific datasets (bgg_data_test/dev/prod, bgg_raw_test/dev/prod)
- **Architecture**: Legacy single-project setup

### Target State
- **Project ID**: bgg-data-warehouse
- **Dataset Structure**: Unified datasets across all environments
  - `analytics` - For dashboard queries (games_active, best_player_counts, filter_options_combined, predictions)
  - `raw` - For raw data tables
  - `core` - For core game data and dimension tables
- **Architecture**: Modern two-project setup (data warehouse + ML predictions)

### Migration Steps

#### 1. Update BigQuery Configuration File
**File**: `config/bigquery.yaml`

Update all three environments (test, dev, prod) to point to bgg-data-warehouse:

**Current**:
```yaml
environments:
  test:
    project_id: gcp-demos-411520
    dataset: bgg_data_test
    raw: bgg_raw_test
  dev:
    project_id: gcp-demos-411520
    dataset: bgg_data_dev
    raw: bgg_raw_dev
  prod:
    project_id: gcp-demos-411520
    dataset: bgg_data_prod
    raw: bgg_raw_prod
```

**Target**:
```yaml
environments:
  test:
    project_id: bgg-data-warehouse
    dataset: analytics
    raw: raw
    location: US
  dev:
    project_id: bgg-data-warehouse
    dataset: analytics
    raw: raw
    location: US
  prod:
    project_id: bgg-data-warehouse
    dataset: analytics
    raw: raw
    location: US
```

**Rationale**: All environments now point to the same datasets in the production data warehouse, simplifying the architecture and ensuring consistency across test/dev/prod.

#### 2. Verify .env File
**File**: `.env`

**Status**: ✅ Already updated to `GCP_PROJECT_ID=bgg-data-warehouse`

No changes needed - this file is already correctly configured.

#### 3. Update GitHub Actions Workflow

**File**: `.github/workflows/cloud-run-deploy.yml`

**Status**: ✅ Updated to use `PROJECT_ID: bgg-data-warehouse`

Changed line 9 from using a GitHub repository variable (`${{ vars.GCP_PROJECT_ID }}`) to a hardcoded environment variable. This ensures the Cloud Run deployment workflow uses the correct project ID.

#### 4. Verify Service Account Permissions
**Files**: `credentials/bgg-sa-key.json` and `credentials/service-account-key.json`

**Action Required**:
Verify that the service accounts have the necessary permissions on the `bgg-data-warehouse` project:
- BigQuery Data Viewer (to read tables)
- BigQuery Job User (to run queries)

**Verification Command**:
```bash
gcloud projects get-iam-policy bgg-data-warehouse --flatten="bindings[].members" --filter="bindings.members:serviceAccount:*@*"
```

#### 5. Test the Migration

After making the configuration changes, test each environment:

**Test Environment**:
```bash
ENVIRONMENT=test python -c "from src.config import get_bigquery_config; print(get_bigquery_config('test'))"
```

**Dev Environment**:
```bash
ENVIRONMENT=dev python -c "from src.config import get_bigquery_config; print(get_bigquery_config('dev'))"
```

**Prod Environment**:
```bash
ENVIRONMENT=prod python -c "from src.config import get_bigquery_config; print(get_bigquery_config('prod'))"
```

Expected output should show:
- `project.id`: `bgg-data-warehouse`
- `project.dataset`: `analytics`
- `datasets.raw`: `raw`

#### 6. Verify Table Access

Run a simple query to verify access to the key tables:

```python
from src.data.bigquery_client import BigQueryClient

client = BigQueryClient(environment='dev')

# Test games_active
query = "SELECT COUNT(*) as count FROM `${project_id}.${dataset}.games_active`"
result = client.execute_query(query)
print(f"games_active count: {result['count'].iloc[0]}")

# Test best_player_counts
query = "SELECT COUNT(*) as count FROM `${project_id}.${dataset}.best_player_counts`"
result = client.execute_query(query)
print(f"best_player_counts count: {result['count'].iloc[0]}")

# Test filter_options_combined
query = "SELECT COUNT(*) as count FROM `${project_id}.${dataset}.filter_options_combined`"
result = client.execute_query(query)
print(f"filter_options_combined count: {result['count'].iloc[0]}")

# Test predictions
query = "SELECT COUNT(*) as count FROM `${project_id}.${dataset}.predictions`"
result = client.execute_query(query)
print(f"predictions count: {result['count'].iloc[0]}")
```

### Files Modified

1. ✅ `config/bigquery.yaml` - Updated all environment configurations
2. ✅ `.github/workflows/cloud-run-deploy.yml` - Updated PROJECT_ID environment variable
3. ⚠️ Service account permissions - Verify via gcloud CLI or GCP Console

### Files Already Correct

1. ✅ `.env` - Already points to bgg-data-warehouse
2. ✅ `src/config.py` - No changes needed (uses config from yaml)
3. ✅ `src/data/bigquery_client.py` - No changes needed (uses template variables)
4. ✅ All SQL queries - No changes needed (use ${project_id} and ${dataset} templates)

### Risk Assessment

**Low Risk Migration** - The changes are primarily configuration updates with minimal code impact:

✅ **Advantages**:
- Code uses template variables, so no query changes needed
- .env file already updated
- Table names are identical between old and new projects
- Can test in dev environment before changing prod

⚠️ **Considerations**:
- Ensure service accounts have permissions on bgg-data-warehouse
- All environments will share the same data (no separate test/dev data)

### Rollback Plan

If issues arise, rollback is simple:

1. Revert `config/bigquery.yaml` to previous state (git revert)
2. Revert `.github/workflows/cloud-run-deploy.yml` to previous state (git revert)
3. No code changes needed

### Success Criteria

✅ Configuration files updated
✅ GitHub Actions workflow updated
✅ Service account permissions verified
✅ Test queries return data successfully
✅ Dashboard loads without errors
✅ All filters and visualizations work correctly

### Post-Migration

After successful migration:
1. Monitor application logs for any BigQuery errors
2. Verify dashboard performance is acceptable
3. Update any documentation referencing the old project
4. Consider decommissioning access to gcp-demos-411520 data (after verification period)
