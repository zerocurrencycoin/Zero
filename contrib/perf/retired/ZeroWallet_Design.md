# zerowallet Design System

Investigation of UI styling in zerowallet400 (Qt5 desktop wallet). Last reviewed: 2026-06-26.

## Summary

zerowallet has no formal design-token layer or component library. Visual styling is implemented as **Qt Style Sheets** (`.css` files under `res/css/`) loaded once on `MainWindow` and inherited by child widgets and dialogs. Five themes are user-selectable; two additional legacy themes exist in resources but are not exposed in Settings.

```
main.cpp (Linux font) -> MainWindow ctor -> QFile(":/css/res/css/{theme}.css") -> setStyleSheet()
Settings -> comboBoxTheme -> slot_change_theme() -> reload CSS
```

There is no `QPalette` usage, no OS dark-mode integration, and no shared C++ color constants.

---

## Theme Architecture

### Loading

Theme CSS is applied in `MainWindow` **before** `ui->setupUi(this)`:

```33:49:src/mainwindow.cpp
	// Include css
    QString theme_name;
    try
    {
       theme_name = Settings::getInstance()->get_theme_name();
    }
    catch (...)
    {
        theme_name = "default";
    }

    QFile qFile(":/css/res/css/" + theme_name +".css");
    if (qFile.open(QFile::ReadOnly))
    {
      QString styleSheet = QLatin1String(qFile.readAll());
      this->setStyleSheet(styleSheet);
    }
```

Runtime switching clears and reloads the stylesheet:

```1963:1984:src/mainwindow.cpp
void MainWindow::slot_change_theme(const QString& theme_name)
{
    Settings::getInstance()->set_theme_name(theme_name);
    // ...
    QFile qFile(":/css/res/css/" + saved_theme_name +".css");
    if (qFile.open(QFile::ReadOnly))
    {
      QString styleSheet = QLatin1String(qFile.readAll());
      this->setStyleSheet(""); // try to reset styles
      this->setStyleSheet(styleSheet);
    }
}
```

Persistence: `QSettings` key `options/theme_name`, default `"zero"` (`src/settings.cpp`).

### Available Themes

| Theme | In Settings UI | Lines | Family | Description |
|-------|----------------|-------|--------|-------------|
| `zero` | Yes (default) | 197 | Immersive | `zero.jpg` background, gold accent `rgb(255, 215, 0)`, semi-transparent black panels |
| `matrix` | Yes | 197 | Immersive | `matrix.jpg` background, green accent `rgb(0, 128, 0)` |
| `light` | Yes | 289 | Flat | Light gray/white base, teal tab headers |
| `blue` | Yes | 287 | Flat | Teal base `#01698c`, darker group boxes `#014d67` |
| `dark` | Yes | 283 | Flat | Charcoal base `#303335`, light text `#c5cad3` |
| `classic` | No | 361 | Flat (legacy) | Gradient tabs/menus, blue checkbox/scrollbar images |
| `default` | No | 87 | Flat (legacy) | Minimal teal base; fallback when settings read fails |

Settings combo options (`src/settings.ui` `comboBoxTheme`): `zero`, `light`, `blue`, `dark`, `matrix`.

Planned but not implemented: **Midnight** theme (`TODO.md`).

### Theme Families

**Immersive (`zero`, `matrix`)**

- `QMainWindow` uses `border-image` from `:/backgrounds/res/images/backgrounds/{zero|matrix}.jpg`
- Most widgets: `background: transparent`, `color: #ffffff`
- Panels/tables: `rgba(0, 0, 0, 128)` overlays
- Inputs: `rgba(64, 64, 64, 128)`, `border-radius: 4px`, `padding: 5px`
- Selection/hover borders: gold (`zero`) or green (`matrix`)
- Dialogs: solid `rgb(0, 0, 0)` background
- Partial widget coverage (~197 lines); no custom scrollbar/checkbox images

**Flat (`light`, `blue`, `dark`, `classic`, `default`)**

- Solid `background-color` on base widgets
- Full styling for tabs, tables, scrollbars, buttons, checkboxes, status bar
- Checkbox and scrollbar arrows use shared PNGs from `:/images/blue/`
- `classic` adds gradient tabs via `qlineargradient`; `default` is a shortened variant

### Reference layout: Wallet Info tab (last main nav tab)

The rightmost tab in the main `QTabWidget` is **Wallet Info** (`tab_6` in `mainwindow.ui`). It is the clearest example of the immersive theme pattern because most of the tab surface is transparent, so the window background image shows through.

**Tab order** (left to right): Overview -> Balances -> Send -> Receive -> ZeroNodes -> **Wallet Info**.

**Layout** (`gridLayout_7`):

| Column | Content |
|--------|---------|
| Left (`groupBox_7`) | Node/wallet stats -- version, protocol, block height, connections, chain value |
| Center (`zerologo`) | Centered `zerodlogo.gif`, scaled to 256x256 in `setupZcashdTab()` |
| Right (`zeroNodeGroup`) | ZeroNode stats -- totals, ROI, daily income, locked coins |

Section headers use 14pt labels (`nodeVersionLabel_2` "Wallet Information", `nodeVersionLabel_3` "ZeroNode Information"). Row values use a `label | value` pattern with right-aligned values.

**Background image** (immersive themes only):

Applied on `QMainWindow`, not on the tab widget itself:

```11:15:res/css/zero.css
QMainWindow
{
    border-image: url(':backgrounds/res/images/backgrounds/zero.jpg') 0 0 0 0 stretch stretch;
    color: #ffffff;
}
```

Asset: `res/images/backgrounds/zero.jpg` (2048x1152 JPEG). `matrix` theme uses the same pattern with `matrix.jpg`.

**Color setup paired with the image** (`zero` theme):

| Layer | Rule | Colors |
|-------|------|--------|
| Base widgets | `background: transparent` | Image visible; text `#ffffff` |
| Tab content pane | `QTabWidget::pane` | `rgba(0, 0, 0, 128)` fill, `rgb(255, 215, 0)` gold border |
| Tab bar | `QTabBar::tab` | `rgba(0, 0, 0, 128)`; gold bottom border; selected tab gold outline |
| Info panels | `QGroupBox` | `rgba(0, 0, 0, 128)` -- semi-transparent black over the photo |
| Labels | inherited | `#ffffff` on transparent background |
| Inputs (if any) | `QLineEdit`, etc. | `rgba(64, 64, 64, 128)` fill; gold border on hover/focus |

`matrix` theme substitutes green accent `rgb(0, 128, 0)` and green-tinted input fills (`rgba(0, 16, 0, 128)`) for the same structure.

**Flat themes on this tab:** `QMainWindow` has a solid fill (`#fcfcfc`, `#01698c`, or `#303335`), so the JPEG never appears. Group boxes pick up the theme's solid `background-color` instead of the immersive overlay pattern.

There is no tab-specific CSS or per-page stylesheet; Wallet Info inherits the global theme from `MainWindow::setStyleSheet()`.

---

## Color Reference

Colors are duplicated per theme file. There is no single source of truth.

### Flat theme palette

| Token (informal) | light | blue | dark |
|------------------|-------|------|------|
| Page background | `#fcfcfc` | `#01698c` | `#303335` |
| Body text | `#303335` | `#c5cad3` / `#f2f0f0` labels | `#c5cad3` |
| Tab bar (unselected) | `#014d67` on `#babec2` border | `#014d67` | `#212121` on `#525355` border |
| Tab bar (selected) | `#01698c` | `#014d67` | `#141414` |
| Tab hover | `#01698c` | `#0698c9` | `#747577` |
| Table header | `#014d67` / `#e6e6e6` row | `#014d67` | `#212121` |
| Group box | `#e6e6e6` | `#014d67` | (inherits base) |
| Accent hover | `#01698c` | `#0698c9` | `#747577` |

### Immersive theme palette

| Token | zero | matrix |
|-------|------|--------|
| Text | `#ffffff` | `#ffffff` |
| Accent / selection border | `rgb(255, 215, 0)` gold | `rgb(0, 128, 0)` green |
| Panel overlay | `rgba(0, 0, 0, 128)` | same |
| Input background | `rgba(64, 64, 64, 128)` | same |
| Selected item fill | `rgb(96, 96, 96)` | same |
| Disabled menu text | `rgb(128, 128, 128)` | same |

### Semantic colors (outside themes)

Applied programmatically or inline, not theme-aware:

| Usage | Mechanism | Files |
|-------|-----------|-------|
| Unconfirmed tx / UTXO | `Qt::red` via `Qt::ForegroundRole` | `txtablemodel.cpp`, `balancestablemodel.cpp` |
| Confirmed data | `Qt::black` | same models |
| Validation errors | `setStyleSheet("color: red;")` | `memoedit.cpp`, `mainwindow.cpp` |
| Warning labels | `color: red` in `.ui` | `confirm.ui`, `zboard.ui`, etc. |
| QR code modules | `QColor(Qt::black)` on white | `qrcodelabel.cpp` |
| QR label background | `#fff` in `.ui` | `mainwindow.ui`, `mobileappconnector.ui` |

**Limitation:** `Qt::black` / `Qt::red` foreground in table models can clash with dark themes that expect light text.

---

## Typography

### Application font

Linux only (`src/main.cpp`):

```213:216:src/main.cpp
        #ifdef Q_OS_LINUX
            QFontDatabase::addApplicationFont(":/fonts/res/Ubuntu-R.ttf");
            qApp->setFont(QFont("Ubuntu", 11, QFont::Normal, false));
        #endif
```

Windows and macOS use the system default font. Font file: `res/Ubuntu-R.ttf` (bundled via `application.qrc` prefix `/fonts`).

### CSS font sizes (flat themes)

| Element | Size | Weight |
|---------|------|--------|
| Table header (`QHeaderView::section`) | 11px | bold |
| Table cells, buttons | 12px | normal |
| Immersive tab labels | (inherit) | bold when selected |

### Monospace

Address fields use `QFontDatabase::systemFont(QFontDatabase::FixedFont)` in `sendtab.cpp` (send tab and confirm dialog).

### Bold headers in models

`Qt::FontRole` with `setBold(true)` in: `balancestablemodel.cpp`, `txtablemodel.cpp`, `localzntablemodel.cpp`, `globalzntablemodel.cpp`, `settings.cpp`, `recurring.cpp`.

### Rich text

`about.ui` embeds HTML with `font-family:'Ubuntu'; font-size:11pt`.

---

## Layout and Spacing

### Global Qt Designer defaults

`src/mainwindow.ui`:

```xml
<layoutdefault spacing="6" margin="11"/>
```

This convention is mirrored in code. Example from `sendtab.cpp` `addAddressSection`: `setSpacing(6)`, `setContentsMargins(11, 11, 11, 11)`.

### CSS spacing (flat themes)

| Element | Values |
|---------|--------|
| Tab padding | 20px H, 5px V |
| Table header | `min-height: 25px`; padding 5px H, 2px V |
| Buttons | padding 15px H, 5px V; `border-radius: 13px`; `min-height: 15px` |
| Scrollbars | 18px width/height; 18px track margin |
| Checkboxes | 5px spacing; 16x16px indicator |
| Status bar | `height: 36px` |

### CSS spacing (immersive themes)

| Element | Values |
|---------|--------|
| Menu bar | `spacing: 25px`; items `padding: 10px` |
| Tabs | `min-width: 150px`; `padding: 4px`; `border-radius: 4px` |
| Inputs | `padding: 5px`; `border-radius: 4px`; `min-width: 100px` |

### Dialog geometry

Settings dialog: `mainwindow.cpp` applies a 50px margin inset via `setGeometry(ps.marginsRemoved(margin))`.

Connection splash (`connection.ui`): root layout uses zero margins (full bleed).

---

## Custom Widgets

| Class | File | Role |
|-------|------|------|
| `QRCodeLabel` | `qrcodelabel.{h,cpp}` | Square label; paints QR on white with black modules. Promoted in `mainwindow.ui`, `mobileappconnector.ui`, `turnstile.ui`, `requestdialog.ui`. |
| `MemoEdit` | `memoedit.{h,cpp}` | `QPlainTextEdit` with byte-length validation; toggles red label and disables accept when over limit. |
| `AddressCombo` | `addresscombo.{h,cpp}` | `QComboBox` showing address + balance. No custom painting. |
| `FilledIconLabel` | `fillediconlabel.{h,cpp}` | Centers/scales pixmap on white fill. **Defined but unused** in any `.ui`. |

All other UI uses standard Qt widgets styled by CSS.

---

## Assets and Resources

Single resource file: `application.qrc` (linked in `zero-qt-wallet.pro`).

| Prefix | Contents |
|--------|----------|
| `/fonts` | `Ubuntu-R.ttf` |
| `/icons` | `icon.ico`, `connected.gif`, `loading.gif`, `paymentreq.gif` |
| `/img` | `zerodlogo.gif`, `logobig.gif`, `zero.png` |
| `/css` | All 7 theme files |
| `/images/blue` | Checkbox + scrollbar arrow PNGs (8 files) |
| `backgrounds` | `zero.jpg`, `matrix.jpg` |
| `icons` | `tick-white.png`, `tick.png`, `close.png` (dialog buttons in `zero.css`) |
| `/translations` | 9 locale `.qm` files |

**Outside qrc:** `res/zero.xpm` -- Linux desktop icon.

### Runtime asset usage

| Asset | Used in |
|-------|---------|
| `icon.ico` | `main.cpp`, `mainwindow.ui`, `rpc.cpp` |
| `loading.gif` | `mainwindow.cpp` status bar |
| `connected.gif`, `paymentreq.gif` | `rpc.cpp`, `txtablemodel.cpp`, `requestdialog.cpp` |
| `zerodlogo.gif` | `mainwindow.cpp` splash |
| `logobig.gif`, `zero.png` | `connection.cpp` |
| Theme backgrounds | `zero.css`, `matrix.css` |
| Blue UI images | `light.css`, `blue.css`, `dark.css`, `classic.css` |

---

## Inline Style Overrides

Styles defined outside theme CSS:

### C++ `setStyleSheet`

| File | Trigger |
|------|---------|
| `memoedit.cpp` | Memo over max length -> `color: red` |
| `mainwindow.cpp` | Turnstile insufficient balance; z-board memo size |

### `.ui` embedded styles

| File | Style |
|------|-------|
| `mainwindow.ui` | Sync warnings (`color: red`); QR labels (`background-color: #fff`) |
| `confirm.ui` | Warning labels |
| `zboard.ui`, `requestdialog.ui`, `mobileappconnector.ui`, `createzcashconfdialog.ui` | Warning/error labels |

These overrides do not adapt when the user switches themes.

---

## Adding or Modifying a Theme

1. Create `res/css/{name}.css`. Follow either the immersive pattern (`zero.css`) or flat pattern (`dark.css`) depending on intent.
2. Register in `application.qrc` under prefix `/css`.
3. Add combo item in `src/settings.ui` `comboBoxTheme` if user-selectable.
4. Rebuild; theme name must match filename without extension.

Flat themes that use checkboxes/scrollbars should reference existing `:/images/blue/` assets or add new PNGs to qrc.

For immersive themes, add a background JPEG under `res/images/backgrounds/` and register under the `backgrounds` qrc prefix.

---

## Gaps and Known Issues

1. **No design tokens** -- colors and spacing are copy-pasted across 7 CSS files (~1700 lines total).
2. **No OS theme sync** -- no `QStyleHints` or platform dark-mode detection.
3. **Theme-unaware data colors** -- table models hardcode `Qt::black` / `Qt::red`.
4. **Inline red/white overrides** -- validation and QR backgrounds ignore theme palette.
5. **Legacy themes orphaned** -- `classic` and `default` in qrc but not in Settings UI.
6. **Unused widget** -- `FilledIconLabel` has no `.ui` references.
7. **Two theme structures** -- immersive themes lack scrollbar/checkbox styling that flat themes provide; visual parity across themes is incomplete.
8. **Midnight theme** -- mentioned in `TODO.md`, not implemented.

---

## Key Files

| File | Purpose |
|------|---------|
| `res/css/*.css` | Theme definitions (primary design surface) |
| `application.qrc` | Asset registry |
| `src/mainwindow.cpp` | Theme load/switch, logo, loading animation |
| `src/mainwindow.ui` | Main layout, promoted widgets, `layoutdefault` |
| `src/settings.{h,cpp,ui}` | Theme picker and persistence |
| `src/main.cpp` | App icon, Linux Ubuntu font |
| `src/qrcodelabel.{h,cpp}` | QR rendering |
| `src/memoedit.{h,cpp}` | Memo validation styling |
| `src/sendtab.cpp` | Dynamic send UI layout, monospace fonts |
| `src/*tablemodel.cpp` | Table header fonts, foreground colors |
| `src/connection.{cpp,ui}` | Splash/connection branding |
