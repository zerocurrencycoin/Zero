// Copyright (c) 2021 Team Zero developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#ifndef ZERONODEPAGE_H
#define ZERONODEPAGE_H

#include <QDialog>
#include <QModelIndex>

class GlobalZNTableModel;
class LocalZNTableModel;
class WalletModel;
class PlatformStyle;
class ZeroNodeSetup;

namespace Ui {
    class ZeroNodePage;
}

QT_BEGIN_NAMESPACE
class QMenu;
QT_END_NAMESPACE

/** Widget that shows a list of zeronodes.
  */

class ZeroNodePage : public QDialog
{
    Q_OBJECT

public:

    explicit ZeroNodePage(const PlatformStyle *_platformStyle, QWidget *parent);
    ~ZeroNodePage();

    void setGlobalModel(GlobalZNTableModel *gzModel);
    void setLocalModel(LocalZNTableModel *lzModel);
    void setWalletModel(WalletModel *walletModel);


public Q_SLOTS:
    void editZeroNode();
    /** Set button states based on selection */
    void selectionChanged();
    /** Spawn contextual menu (right mouse menu) for local zeronodes */
    void contextualMenu(const QPoint &point);

private:
    Ui::ZeroNodePage *ui;
    const PlatformStyle *platformStyle;
    GlobalZNTableModel *gzModel;
    LocalZNTableModel *lzModel;
    WalletModel *walletModel;
    QMenu *contextMenu;
    QAction *startAction;
    QAction *enableAction;
    QAction *disableAction;
    QAction *editAction;
    QAction *deleteAction;
    QModelIndex index;

// private Q_SLOTS:


// Q_SIGNALS:

};







#endif // ZERONODEPAGE_H
