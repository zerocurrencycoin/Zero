// Copyright (c) 2021 Team Zero developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#ifndef ZERONODESETUP_H
#define ZERONODESETUP_H

#include <QDialog>

class WalletModel;
class PlatformStyle;

namespace Ui {
    class ZeroNodeSetup;
}

/** Widget used to setup new ZeroNodes.*/
class ZeroNodeSetup : public QDialog
{
    Q_OBJECT

public:

    explicit ZeroNodeSetup(const PlatformStyle *platformStyle, QWidget *parent);
    ~ZeroNodeSetup();

    void setWalletModel(WalletModel *walletModel);

public Q_SLOTS:
    void setAlias(QString alias);
    void setIpAddress(QString alias);
    void setPrivateKey(QString alias);
    void setOutput(QString alias);
    void setIndex(QString alias);

private:
    Ui::ZeroNodeSetup *ui;
    WalletModel *walletModel;


// private Q_SLOTS:


// Q_SIGNALS:

};

#endif // ZERONODESETUP_H
