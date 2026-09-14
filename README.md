# IUP Regression Model

Graphical tool for estimating long-term trends in monthly atmospheric datasets with multiple linear regression (MLR).

The model was developed at the Institute of Environmental Physics (IUP), University of Bremen, primarily for vertically and/or geographically resolved ozone time series. It can combine a trend and intercept with standard atmospheric proxies, user-supplied proxies, seasonal terms, optional inflection points, anomaly calculations, and data-coverage filters. The regression is evaluated independently for every non-time grid cell.

> **Development status:** alpha 1.30 (`alpha1.3` branch). This is research software under active development. Validate configurations and results before scientific use. See [Known limitations](#known-limitations).

## Contents

- [What the model does](#what-the-model-does)
- [Quick start](#quick-start)
- [Using the graphical interface](#using-the-graphical-interface)
- [Input data](#input-data)
- [Configuration reference](#configuration-reference)
- [Regression terms and inflection points](#regression-terms-and-inflection-points)
- [Data filtering](#data-filtering)
- [Output](#output)
- [Python API](#python-api)
- [Troubleshooting](#troubleshooting)
- [Known limitations](#known-limitations)
- [Repository structure](#repository-structure)

## What the model does

For each spatial or vertical cell, the program:

1. reads a monthly dependent variable from a NetCDF file;
2. aligns the dataset and all enabled proxies on a continuous monthly time axis;
3. restricts the calculation to their common time period and the configured start/end dates;
4. optionally converts the data to absolute or relative monthly anomalies or averages selected months by calendar year;
5. rejects trend segments that do not satisfy the configured coverage criteria;
6. constructs an independent-variable matrix from the trend, intercept, and proxies;
7. performs an initial ordinary least-squares fit and a second fit with an estimated lag-1 autocorrelation correction; and
8. returns the trend, trend uncertainty, coefficient-to-standard-error ratio, fitted coefficients, diagnostics, and plotting data.

The bundled standard proxies are read from `data/Proxies_Timeseries_202503.txt` and `data/AOD_timeseries_1980-2022_10lat.txt`:

| Index | Proxy |
| ---: | --- |
| 0 | ENSO 3.4 |
| 1 | Solar |
| 2 | QBO1 |
| 3 | QBO2 |
| 4 | EHF Northern Hemisphere |
| 5 | EHF Southern Hemisphere |
| 6 | Arctic Oscillation (AO) |
| 7 | Antarctic Oscillation (AAO) |
| 8 | Latitude-dependent aerosol optical depth (AOD) |

Proxy indices in configuration keys such as `default_proxy_0_method` are **zero-based**.

## Quick start

### 1. Download the code

Clone the `alpha1.3` branch or download and extract its ZIP archive:

```bash
git clone --branch alpha1.3 https://github.com/IUPBAuf/IUP-Regression-Model.git
cd IUP-Regression-Model
```

Always start the program from the repository root. Several UI and data paths are resolved relative to the current working directory.

### 2. Create an isolated Python environment

Python 3.12 is recommended for this branch and was used to verify this README.

Linux/macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install statsmodels
```

### 3. Start the application

It is now possible to start the program with the pre-made config.ini and the test dataset (SAGE-SCIA-OMPS).

```bash
python iup_regression_model.py --ui
```

## Using the graphical interface

### Overview tab

1. Select the dataset in **Datasets**.
2. Limit each non-time dimension with the **Data Limits** controls if a subset is sufficient. This can greatly reduce computation time.
3. Enter optional `YYYY-MM` start and end dates.
4. Optionally enter one or more comma-separated inflection points and choose a method for every resulting segment.
5. Optionally enter months to average, for example `1, 2, 12`, or use `yearly`/`all` for an annual mean. Selected months are grouped within each calendar year.
6. Enable absolute or relative anomalies if needed.
7. Choose a method for the trend, intercept, and each proxy. Seasonal-component selectors are active for harmonic terms.
8. Select **Compute**. A progress bar is shown while grid cells are processed.

The method choices are:

| Value | GUI label | Effect |
| ---: | --- | --- |
| 0 | disabled | Exclude the term. |
| 1 | single | Use one coefficient. |
| 2 | harmonics | Use the base term plus sine/cosine modulations. |
| 3 | 12 months | Use separate coefficients for the months of the year. |

Seasonal-component values control the harmonic order:

| Value | GUI label | Added sine/cosine terms |
| ---: | --- | ---: |
| 1 | annual | 2 |
| 2 | semi-annual | 4 |
| 3 | tri-annual | 6 |
| 4 | quarter-annual | 8 |

When a multi-month or annual mean is selected, the GUI resets harmonic and 12-month terms to the single-coefficient method.

### Diagnostic tab

The diagnostic pages display:

- the loaded dependent-variable time series, time span, shape, and number of missing values;
- all proxy time series and their dimensions; and
- the independent-variable matrix after a regression has been computed.

Dataset and proxy table values can be edited in memory. Empty cells are masked, `nan` inserts a missing value, and changed cells are highlighted. **Reset Data** and **Reset Proxy** restore the values originally loaded from disk. These edits do not modify the source files.

### Plotting tab

After computation, the program can create:

- **Model**: observations and fitted model at one selected grid cell, including residual RMS and coefficient of determination (`R²`);
- **Contour**: trend or twice the trend uncertainty across two selected dimensions;
- **Residual**: detrended residual time series at one grid cell;
- **Observations**: valid-observation fraction and segment-filter flags;
- **Proxies**: selected fitted proxy contributions plus residuals at one grid cell; and
- **Proxy Contour**: a fitted proxy coefficient across two dimensions.

Use **File → Save Current Plot** to save the active figure as a 300 dpi PNG or use the matplotlib save figure button. The dialog allows the output size and title visibility to be changed.

### Loading and saving files

- **File → Load Data File** opens a NetCDF variable-selection dialog. Despite the file filter mentioning ASCII, the dependent-data loader in this branch expects NetCDF.
- **File → Load Proxy File** accepts an ASCII or NetCDF proxy and opens the corresponding import settings.
- **File → Save Trend** writes the most recently computed result to NetCDF.
- **Help → Contact** prints `brian@iup.physik.uni-bremen.de` in the terminal from which the program was started.

When saving a trend, enter a filename without `.nc`; the current code appends the extension automatically.

## Input data

### Dependent dataset

The dependent variable must be stored in a NetCDF file. The loader supports any number of dimensions, provided that:

- exactly one dimension represents time;
- `time_dim` identifies its one-based position in the dependent variable;
- every non-time dimension has a readable one-dimensional coordinate variable; and
- the configured variable and dimension names exist in the selected root group or `group_name`.

The time dimension is moved to the first position internally. A typical ozone variable is therefore represented as:

```text
ozone(time, altitude, latitude)
```

or:

```text
ozone(time, altitude, latitude, longitude)
```

Masked values and invalid floating-point values are treated as missing data.

Supported time representations include:

- integers such as `202405` with `%Y%m`;
- integers such as `20240519` with `%Y%m%d`;
- strings such as `2024-05`, `2024/05`, or full dates with a matching `strptime` format;
- fractional years such as `2001.5`; and
- numeric offsets with a configuration such as `days since 2000-01-01` or the shorthand `ds 2000-01-01`.

If `time_var` contains two comma-separated names, the first is treated as the year variable and the second as the month variable.

### Default proxies

`proxy_path` must point to a whitespace-separated table whose first column is used as the index. If a `Month` column is present, the index is interpreted as the year and combined with that month. All remaining columns become separate proxies.

`aod_path` must point to a whitespace-separated file whose first column is `YYYYMM` and whose remaining columns contain AOD for the latitude grid `-85, -75, ..., 85°`.

Default proxy paths are resolved relative to the directory containing `iup_regression_model.py`.

### Additional ASCII proxies

An ASCII proxy is read as a whitespace-separated table without column headers after `additional_proxy_header_size` rows have been skipped. Column numbers are zero-based.

Example:

```ini
additional_proxy_path = /path/to/proxy.txt
additional_proxy_name = My proxy
additional_proxy_time_col = 0
additional_proxy_data_col = 1
additional_proxy_time_format = %Y%m
additional_proxy_header_size = 1
additional_proxy_method = 1
additional_proxy_seas_comp = 2
```

For separate year and month columns, use for example:

```ini
additional_proxy_time_col = 0, 1
additional_proxy_data_col = 2
```

For a two-dimensional ASCII proxy, `additional_proxy_data_col` is the first of all remaining data columns. Add a dimension tag and either explicit coordinate values or `start, end, step`:

```ini
additional_proxy_tag = lat
additional_proxy_tag_array = -85, 85, 10
```

### Additional NetCDF proxies

For a NetCDF proxy, `additional_proxy_data_col` and `additional_proxy_time_col` are variable names rather than numeric column numbers. A second name in `additional_proxy_time_col` is interpreted as a separate month variable.

To configure multiple additional proxies, repeat the complete block for each proxy. Place each `additional_proxy_path` first in its block because this key advances the parser to the next proxy.

Additional-proxy paths are used as written, so absolute paths are safest. Relative paths are interpreted from the current working directory.

## Configuration reference

Lines beginning with `#` or `;` are comments. Blank lines and lines without `=` are ignored. Except for repeated additional-proxy blocks, each active key should occur only once.

### Dataset and dimensions

| Key | Meaning |
| --- | --- |
| `data_path` | Path to the dependent NetCDF file. Required at GUI startup. |
| `group_name` | Optional NetCDF group containing the variables. Omit for the root group. |
| `o3_var` | Name of the dependent variable. Despite the historical name, the code can process another atmospheric quantity. |
| `o3_var_unit` | Display/output label for the dependent variable. The code does not perform unit conversion. |
| `time_var` | Time-variable name, or `year_var, month_var`. Default: `time`. |
| `time_dim` | One-based position of time in `o3_var`. Default: `1`. |
| `time_format` | Python `strptime` format or numeric-offset form such as `days since YYYY-MM-DD`. |
| `additional_var_N_index` | Coordinate-variable name used for dimension position `N`. Defaults to the dimension name. |
| `additional_var_N_tag` | Semantic tag such as `lat`, `lon`, or `alt`; used to match multidimensional proxies. |
| `additional_var_N_unit` | Axis label stored for plotting. |
| `additional_var_N_limit` | Zero-based index or inclusive `min, max` indices. In the GUI, use the Data Limits controls because startup populating currently resets configured limits. |
| `tag_name_lat`, `tag_name_lon`, `tag_name_alt`, `tag_name_time` | Comma-separated aliases used by the import dialog to suggest semantic tags. |

Here, `N` is the one-based dimension position in the original dependent variable, including time. For `ozone(time, alt, lat)`, altitude uses `N = 2` and latitude uses `N = 3`.

### Time range, averaging, and anomalies

| Key | Accepted values | Meaning |
| --- | --- | --- |
| `start_date` | `YYYY-MM` | Optional first analysis month. |
| `end_date` | `YYYY-MM` | Optional last analysis month. |
| `averaging_window` | `yearly`, `all`, or unique months from `1` to `12` | Produces one value per calendar year using all or selected months. Omit for monthly regression. |
| `anomaly` | `True` / `False` | Enables anomaly calculation. String matching is case-sensitive. |
| `anomaly_method` | `abs` / `rel` | Absolute difference from the climatological mean or relative difference divided by that mean. Default: `rel`. |
| `skip_percentage` | fraction from `0` to `1` | Minimum usable fraction for averaged data and month-specific terms. Default: `0.75`. |

Without averaging, anomalies are calculated separately for each calendar month. With averaging, the anomaly is calculated relative to the mean of the resulting annual series.

### Model terms

| Key | Accepted values | Meaning |
| --- | --- | --- |
| `trend_method` | `0`, `1`, `2`, `3` | Method for trend terms. Default: `1`. |
| `intercept_method` | `0`, `1`, `2`, `3` | Method for intercept terms. Default: `1`. |
| `default_proxy_method` | `0`, `1`, `2`, `3` | Fallback method for all standard proxies. |
| `default_proxy_K_method` | `0`, `1`, `2`, `3` | Override for zero-based standard proxy index `K`. |
| `default_seasonal_component` | `1`–`4` | Fallback harmonic order. Default: `2`. |
| `trend_seasonal_component` | `1`–`4` | Harmonic order for the trend. |
| `intercept_seasonal_component` | `1`–`4` | Harmonic order for the intercept. |
| `default_proxy_K_seasonal` | `1`–`4` | Harmonic order for zero-based standard proxy index `K`. |
| `default_proxy_limit` | `0` / `1` | If `1`, applies hemisphere limits to EHF, AO, and AAO proxy objects. This boundary logic is currently not enforced when the design matrix is built; see limitations. |

### Inflection points and gaps

| Key | Meaning |
| --- | --- |
| `inflection_point` | One or more ordered, comma-separated `YYYY-MM` dates. |
| `inflection_method` | Comma-separated method for each resulting segment: `ind`, `pwl`, or `gap`. |

With two inflection points there are three segments, so three methods are required. If fewer methods are supplied, the code repeats the supplied list to fill the segments.

- `ind`: fit an independent intercept and trend for the segment;
- `pwl`: fit a continuous piecewise-linear trend; and
- `gap`: exclude that segment from trend output while allowing a discontinuity between surrounding independent segments.

`pwl` cannot be mixed with `ind` or `gap` in one calculation. A configuration containing only `gap` segments is invalid.

Example with an excluded middle interval:

```ini
inflection_point = 1996-01, 2000-01
inflection_method = ind, gap, ind
```

### Coverage filters

Filters are applied separately to every non-gap trend segment and grid cell.

| Key | Default | Meaning |
| --- | ---: | --- |
| `filter_fill_fraction` | `0.70` | Minimum temporal span between the first and last valid observation relative to the full segment length. |
| `filter_internal_fraction` | `0.50` | Minimum valid-data fraction between the first and last valid observation. |
| `filter_max_gap_length` | disabled | Maximum consecutive missing run. Values below `1` are interpreted as a fraction of the covered core length; values of at least `1` are time-step counts. |
| `filter_min_core_length` | `0` | Skip the maximum-gap test when the covered core is shorter than this number of time steps. |

Filter flags used by the Observations plot are:

| Flag | Meaning |
| ---: | --- |
| 0 | segment accepted |
| 1 | no valid data |
| 2 | insufficient temporal coverage |
| 3 | insufficient internal density |
| 4 | excessive consecutive gap |

## Regression terms and inflection points

The matrix begins with intercept and trend terms and then adds each enabled proxy. Standard proxies are normalised over their usable period; AOD uses a separate zero-aware min/max treatment. Multidimensional proxies are matched to a dependent-data dimension through their semantic tag. If the requested coordinate is not present, the code linearly interpolates between the two closest proxy coordinates.

The first coefficient vector is obtained with ordinary least squares. The code then estimates lag-1 residual autocorrelation while excluding discontinuities across missing time steps, transforms the design matrix and observations, and performs the reported second fit. Trend values are scaled to per-decade units: monthly coefficients are multiplied by 120, while annually averaged coefficients are multiplied by 10. Anomaly calculations introduce additional scaling in the current implementation; independently verify the units before publication.

The variable named `significance` in the NetCDF output is the absolute coefficient divided by its estimated standard error (`|β/SE|`). It is **not** a p-value.

## Data filtering

The program first intersects the configured analysis interval with the dependent dataset and every enabled proxy. It then creates a complete monthly time axis and inserts `NaN` wherever a dataset or proxy has no value. This means an enabled proxy with a shorter record shortens the usable model period for all variables.

Coverage filtering occurs before fitting. A failed segment is replaced with missing values for that grid cell and receives the corresponding flag. The Observations plot shows both the retained fraction and why a segment was rejected.

## Output

### GUI NetCDF output

**File → Save Trend** writes:

| Variable | Contents |
| --- | --- |
| coordinate variables | All non-time coordinates retained for the calculation. |
| `date` | Analysis dates as `YYYY-MM-DD` strings. |
| `fractional_year` | Dates converted to fractional years. |
| `independent_variable_names` | Human-readable design-matrix column names. |
| `independent_variable_matrix` | Matrix used for each time and grid cell. |
| `beta` | Autocorrelation-corrected fit coefficients. |
| `beta_uncertainty` | Standard errors of those coefficients. |
| `ozone_time_series` | Dependent time series after alignment, filtering, averaging, and/or anomaly processing. |
| `trend` | Trend per grid cell and, where applicable, non-gap segment. |
| `significance` | Absolute trend coefficient divided by its standard error. |
| `trend_uncertainty` | Estimated standard error of the scaled trend. |

Global attributes include the program/version, contact, creation date, and the active configuration. The output does not include the observation-filter flags or fractions; these are available in memory and in the Observations plot.

### Return values

`iup_reg_model(data, proxies, ini)` returns:

```python
trends, significance, diagnostic = iup_reg_model(data, proxies, ini)
```

The diagnostic list contains:

| Index | Contents |
| ---: | --- |
| 0 | design matrix for all grid cells |
| 1 | initial ordinary-least-squares coefficients |
| 2 | autocorrelation-corrected coefficients |
| 3 | coefficient standard errors |
| 4 | design-matrix column names |
| 5 | output time coordinate |
| 6 | processed dependent data |
| 7 | trend uncertainty |
| 8 | valid-observation fraction per segment |
| 9 | segment-filter flags |
| 10 | dimension names |

## Python API

The computational functions can be imported without opening the GUI:

```python
from iup_regression_model import (
    iup_reg_model,
    load_additional_proxies,
    load_config_ini,
    load_default_proxies,
    load_netCDF,
)

ini = load_config_ini("config folder/config.ini")
data = load_netCDF(ini["data_path"], ini)
if data is None:
    raise RuntimeError("The dependent NetCDF file could not be loaded")

proxies = load_default_proxies(ini)
proxies = load_additional_proxies(proxies, ini)
trends, significance, diagnostic = iup_reg_model(data, proxies, ini)
```

This is currently a code-level API rather than a stable public package interface. In particular, do not use `save_netCDF(...)` as a batch-output example in alpha 1.30; see the known batch-mode issue below.

## Troubleshooting

### `AttributeError: 'NoneType' object has no attribute 'name'`

The startup dataset was not loaded. Check `data_path`, `group_name`, `o3_var`, coordinate-variable names, `time_var`, `time_dim`, and `time_format`. The repository's committed `data_path` does not refer to a bundled file.

### Qt platform or display error

The normal entry point is graphical and requires a desktop display. Run it from a local graphical session. On a remote Linux machine, use trusted X11 forwarding or another supported remote-desktop setup. Setting an off-screen Qt backend can initialise parts of the interface for testing, but it does not provide an interactive application.

### Data loads with incorrect dates

Provide an explicit `time_format`. For numeric time offsets, copy the reference date into the configuration, for example `days since 1980-01-01`. The loader does not automatically use the NetCDF variable's `units` attribute as the time format.

### Regression reports dependent proxies or produces `NaN`

The design matrix is singular or insufficient data survived filtering. Disable a redundant proxy/term, reduce model complexity, inspect the Diagnostic and Observations pages, or review the filter thresholds. Each active coefficient needs more than two non-zero observations, and the autocorrelation-corrected fit also requires a sufficiently long usable sequence.

### Output is named `result.nc.nc`

Enter `result`, not `result.nc`, in the Save Trend dialog. The application appends `.nc` itself.

### Paths work only from some directories

Start the program from the repository root. `data_path` and additional-proxy paths are interpreted relative to the current working directory, while the bundled default-proxy paths are resolved relative to the script directory.

## Known limitations

The following points describe the current `alpha1.3` code, not planned behaviour:

- The non-GUI save path currently passes mismatched diagnostic-list entries to `save_netCDF()` and fails while writing `independent_variable_names`. Batch execution should therefore be considered unavailable in alpha 1.30.
- The main application uses PyQt5. `regression_model_ui.py`, PySide2, PySide6, `scipy`, and the external `DateTime` package are not used by the active main module, although they are present in the repository or requirements.
- **Save Configuration**, **Load Settings**, and the **Options** menu are present in the UI files but are not connected to handlers. Presets change visible analysis settings but do not load the dataset or proxy files recorded by the preset.
- The dependent-data file picker advertises ASCII files, but its settings dialog and loader open the selection as NetCDF.
- GUI startup rebuilds the dimension-limit controls and resets `additional_var_N_limit` values. Select limits in the GUI after startup.
- `default_proxy_limit = 1` assigns hemispheric bounds to EHF/AO/AAO proxy objects, but the corresponding boundary check is commented out while constructing the design matrix.
- The output variable `significance` is a coefficient-to-standard-error ratio, not a formal p-value.
- Relative-anomaly trend scaling and combinations of less-common options have not been comprehensively validated. Inspect diagnostics and compare against an independent calculation for scientific production.
- No licence file is included in this branch. Contact the author before redistribution or reuse outside the applicable repository terms.

## Repository structure

```text
IUP-Regression-Model/
├── iup_regression_model.py    # active GUI and regression implementation
├── main.ui                    # main Qt interface
├── data_load.ui               # dependent NetCDF import dialog
├── proxy_load.ui              # proxy import dialog
├── preview_table.ui           # ASCII preview dialog
├── save_plot.ui               # plot export dialog
├── options.ui                 # currently unconnected options dialog
├── var_naming.ui              # additional UI resource
├── regression_model_ui.py     # generated, currently unused PySide2 UI module
├── config folder/
│   └── config.ini             # GUI startup configuration and preset
├── data/
│   ├── SAGE-SCIA-OMPS.nc      # bundled ozone example
│   ├── ESA-CREST-v2.0-fv001.nc
│   ├── Proxies_Timeseries_202503.txt
│   ├── AOD_timeseries_1980-2022_10lat.txt
│   ├── LOTUS_proxies.txt
│   └── settings.ini           # legacy/unused by the active module
├── requirements.txt
└── iupLogo.png
```

## Contact

Brian Auffarth  
Institute of Environmental Physics, University of Bremen  
[brian@iup.physik.uni-bremen.de](mailto:brian@iup.physik.uni-bremen.de)

Repository: <https://github.com/IUPBAuf/IUP-Regression-Model/tree/alpha1.3>
