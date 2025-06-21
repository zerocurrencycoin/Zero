# ZEROV.md

## Transition Planning for Zero

This document outlines the expected impact and complexity of transitioning the Zero cryptocurrency codebase to modern infrastructure dependencies: **Berkeley DB 18.1.40**, **Boost 1.74**, and **Qt 5.9**. These align with upstream updates in Zcash 4.x and 5.x.

---

## 🗄️ Berkeley DB (BDB) – Transition to 18.1.40

### 📌 Impact
- Moving from BDB 4.8 (likely default) to 18.1.40 modernizes wallet database support.
- Enables builds on modern systems without legacy manual compilation.

### ⚠️ Complexity: Moderate to High
- API changes between BDB 4.8 and 18.x (e.g., environment and DB open methods).
- Wallet format and compatibility checks must be validated.
- Build scripts may need refactoring to detect and link modern BDB correctly.

---

## ⚙️ Boost – Upgrade to 1.74

### 📌 Impact
- Improves compatibility with modern Linux distributions.
- Brings stability and bug fixes in filesystem, threading, and test libraries.

### ⚠️ Complexity: Low to Moderate
- Some APIs deprecated or changed since early Boost versions.
- Boost.Test suite syntax may require slight adjustments.

---

## 🖥️ Qt – Upgrade to 5.9

### 📌 Impact
- Enables GUI compatibility with modern OS versions (Windows, macOS, Linux).
- Qt 5.9 is the first long-term support release in Qt 5 series.

### ⚠️ Complexity: Moderate
- GUI must be reviewed for deprecated Qt calls and styling issues.
- Build tooling (e.g., `qmake`, `.pro` files) may need version updates.

---

## ✅ Transition Summary

| Component | Target Version | Impact                            | Complexity        |
|-----------|----------------|------------------------------------|-------------------|
| BDB       | 18.1.40        | Wallet DB compatibility, support   | Moderate–High     |
| Boost     | 1.74           | Build compatibility and stability  | Low–Moderate      |
| Qt        | 5.9            | GUI modernization and portability  | Moderate          |

---

## 🔧 Recommendations

1. Start with **Boost** transition to reduce CI and packaging friction.
2. Follow with **Qt 5.9**, testing GUI behavior across platforms.
3. Transition to **BDB 18.1.40** last, validating wallet behavior with backups.

