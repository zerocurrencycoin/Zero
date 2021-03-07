// Copyright (c) 2021 Team Zero developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#ifndef ZERONODETABLEMODEL_H
#define ZERONODETABLEMODEL_H

#include <QAbstractTableModel>
#include <QString>
#include <QList>
#include <QObject>
#include <QDateTime>
#include <QFont>

class WalletModel;
class CWallet;







struct LocalZeroNodes {
    QString         status;
    QString         alias;
    QString         ipAddress;
    QString         privateKey;
    QString         txid;
    QString         index;
};

struct ZNOutputs {
    QString         txid;
    int             index;
};

extern QList<LocalZeroNodes> zeroNodeSettings;

class LocalZNTableModel: public QAbstractTableModel
{
public:
    LocalZNTableModel(QObject* parent);
    ~LocalZNTableModel();

    void refreshLocalZNData();
    void addLocalZNData();
    void writeZeroNodeNData();

    QString  getLZNStatus(int row) const;
    QString  getLZNAlias(int row) const;
    QString  getLZNIpAddress(int row) const;
    QString  getLZNPrivateKey(int row) const;
    QString  getLZNTxid(int row) const;
    QString  getLZNIndex(int row) const;

    int      rowCount(const QModelIndex &parent) const;
    int      columnCount(const QModelIndex &parent) const;
    QVariant data(const QModelIndex &index, int role) const;
    QVariant headerData(int section, Qt::Orientation orientation, int role) const;


    // void setupZeroNode(MainWindow* main, Ui_znsetup* zn, QDialog* d, const LocalZeroNodes &lineNode);
    // void deleteZeroNodeFromSetup(const LocalZeroNodes &delNode);
    // void writeZeroNodeSetup();
    // void updateZeroNodeSetup(const LocalZeroNodes &lineNode, LocalZeroNodes &updatedNode);
    // void updateZNPrivKeySetup(Ui_znsetup* zn, QString* newKey);
    // void updateZNOutput(Ui_znsetup* zn);
    bool isLocal(QString txid);

private:
    void updateAllLZNData();
    void sortZNData(QList<LocalZeroNodes>* list);

    QList<LocalZeroNodes>*    znData        = nullptr;

    QList<LocalZeroNodes>*    modeldata     = nullptr;

    QList<ZNOutputs>*         outputs       = nullptr;
    int                       outputIndex   = 0;

    QList<QString>            headers;
};







struct GlobalZeroNodes {
    int             rank;
    QString         address;
    int             version;
    QString         status;
    qint64          active;
    QString         lastSeen;
    QString         lastPaid;
    QString         txid;
    QString         ipAddress;
    bool            local;
};


class GlobalZNTableModel : public QAbstractTableModel
{

public:
    GlobalZNTableModel(CWallet *wallet, QObject* parent);
    ~GlobalZNTableModel();

    void refreshGlobalZNData(LocalZNTableModel *lzn);

    int       getGZNRank(int row) const;
    QString   getGZNAddr(int row) const;
    int       getGZNVersion(int row) const;
    QString   getGZNStatus(int row) const;
    int       getGZNActive(int row) const;
    QString   getGZNLastSeen(int row) const;
    QString   getGZNLastPaid(int row) const;
    QString   getGZNTxid(int row) const;
    QString   getGZNIp(int row) const;

    int      rowCount(const QModelIndex &parent) const;
    int      columnCount(const QModelIndex &parent) const;
    QVariant data(const QModelIndex &index, int role) const;
    QVariant headerData(int section, Qt::Orientation orientation, int role) const;

private:
    WalletModel *walletModel;
    CWallet *wallet;

    void updateAllZNData();
    void sortZNData(QList<GlobalZeroNodes>* list);
    QList<GlobalZeroNodes>*   znData        = nullptr;
    QList<GlobalZeroNodes>*   modeldata     = nullptr;
    QList<QString>            headers;
};




#endif // ZERONODETABLEMODEL_H
