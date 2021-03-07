// Copyright (c) 2021 Team Zero developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.


#include "zeronodesetup.h"
#include "ui_zeronodesetup.h"

#include "zeronodetablemodel.h"
#include "netbase.h"
#include "platformstyle.h"

ZeroNodeSetup::ZeroNodeSetup(const PlatformStyle *platformStyle, QWidget *parent) :
    QDialog(parent),
    ui(new Ui::ZeroNodeSetup)
{
    ui->setupUi(this);

}

ZeroNodeSetup::~ZeroNodeSetup()
{
    delete ui;
}

void ZeroNodeSetup::setAlias(QString alias) {
    ui->txtZNAlias->setText(alias);
}

void ZeroNodeSetup::setIpAddress(QString ipAddress) {
    int port = 0;
    std::string hostname = "";
    SplitHostPort(ipAddress.toStdString(), port, hostname);

    CNetAddr node = CNetAddr(hostname, false);
    int nNetwork = node.GetNetwork();
    switch (nNetwork) {
        case 1 :
            ui->txtZNIpAddress->setText(QString::fromStdString(hostname));
            break;
        case 2 :
            ui->txtZNIpAddress->setText(QString::fromStdString("[" + hostname + "]"));
            break;
        case 3 :
            ui->txtZNIpAddress->setText(QString::fromStdString(hostname));
            break;
    }
}

void ZeroNodeSetup::setPrivateKey(QString privateKey) {
    ui->txtZNPrivateKey->setText(privateKey);
}

void ZeroNodeSetup::setOutput(QString output) {
    ui->txtZNOutput->setText(output);
}

void ZeroNodeSetup::setIndex(QString index) {
    ui->txtZNIndex->setText(index);
}
