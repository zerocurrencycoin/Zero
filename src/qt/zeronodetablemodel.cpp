// Copyright (c) 2021 Team Zero developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include "walletmodel.h"
#include "wallet/wallet.h"
#include "zeronode/zeronodeman.h"
#include "zeronode/zeronodeconfig.h"
#include "zeronodetablemodel.h"
#include "key_io.h"
#include "util.h"



QString convertSecondsToDays(qint64 n) {
    QString activeDays = "";

    qint64 day = n / (24 * 3600);
    if (day != 1) {
      activeDays = QString::number(day) + " days ";
    }
    else {
      activeDays = QString::number(day) + " day ";
    }

    n = n % (24 * 3600);
    qint64 hours = n / 3600;

    n %= 3600;
    qint64 minutes = n / 60 ;

    return activeDays + QString::number(hours) + "h:" + QString::number(minutes) + "m";
}

















QList<LocalZeroNodes> zeroNodeSettings;

LocalZNTableModel::LocalZNTableModel(QObject *parent)
     : QAbstractTableModel(parent) {
    headers << QObject::tr("Status") << QObject::tr("Alias") << QObject::tr("IP Address")
            << QObject::tr("Private Key") << QObject::tr("Txid") << QObject::tr("Index");
}

LocalZNTableModel::~LocalZNTableModel() {
    delete modeldata;
    delete znData;
    delete outputs;
}

void LocalZNTableModel::writeZeroNodeNData() {
    // boost::filesystem::path pathZeronodeConfigFile = GetZeronodeConfigFile();
    // if (boost::filesystem::exists(pathZeronodeConfigFile) {
    //     boost::filesystem::remove(pathZeronodeConfigFile);
    // }
    //
    // FILE* configFile = fopen(pathZeronodeConfigFile.string().c_str(), "a");
    // if (configFile != NULL) {
    //     std::string strHeader = "# Zeronode config file\n"
    //                             "# Format: alias IP:port zeronodeprivkey collateral_output_txid collateral_output_index\n"
    //                             "# Example: zn1 127.0.0.1:23801 93HaYBVUCYjEMeeH1Y4sBGLALQZE1Yc1K64xiqgX37tGBDQL8Xg 2bcd3c84c84f87eaa86e4e56834c92927a07f9e18718810b92e0d0324456a67c 0\n";
    //
    //
    //     QList<LocalZeroNodes>::iterator i;
    //     for (i = modeldata->begin(); i != modeldata->end(); ++i) {
    //         LocalZeroNodes lzn = *i;
    //
    //         std::string strLine = lzn.alias + " " + lzn.ipAddress + " " + lzn.privateKey + " " + lzn.txid + " " + lzn.index + "\n";
    //         if (lzn.status == "DISABLED") {
    //             strLine = "#" + strLine;
    //         }
    //
    //         strHeader += strLine;
    //     }
    //
    //     fwrite(strHeader.c_str(), std::strlen(strHeader.c_str()), 1, configFile);
    //     fclose(configFile);
    // }
}

void LocalZNTableModel::refreshLocalZNData() {
    delete znData;
    znData = new QList<LocalZeroNodes>();


    int linenumber = 1;
    boost::filesystem::path pathZeronodeConfigFile = GetZeronodeConfigFile();
    boost::filesystem::ifstream streamConfig(pathZeronodeConfigFile);

    if (!streamConfig.good()) {
        return; // Nothing to read, so just return
    }


    for (std::string line; std::getline(streamConfig, line); linenumber++) {

        if (line.empty()) continue;

        std::istringstream iss(line);
        std::string comment, alias, ip, privKey, txHash, outputIndex;
        bool status = true;
        bool parseable = true;

        if (iss >> comment) {
            if (comment.at(0) == '#') status = false;
            iss.str(line);
            iss.clear();
        }

        if (!(iss >> alias >> ip >> privKey >> txHash >> outputIndex)) {
            iss.str(line);
            iss.clear();
            if (!(iss >> alias >> ip >> privKey >> txHash >> outputIndex)) {
                parseable = false;
            }
        }

        if (parseable) {
            int port = 0;
            std::string hostname = "";
            SplitHostPort(ip, port, hostname);

            LocalZeroNodes lzn;
            if (status) {
                lzn.status = "ENABLED";
            } else {
                lzn.status = "DISABLED";
            }
            lzn.alias = QString::fromStdString(alias);
            lzn.ipAddress = QString::fromStdString(hostname);
            lzn.privateKey = QString::fromStdString(privKey);
            lzn.txid = QString::fromStdString(txHash);
            lzn.index = QString::fromStdString(outputIndex);

            znData->append(lzn);

        }
    }

    streamConfig.close();
    updateAllLZNData();
}

void LocalZNTableModel::addLocalZNData() {
    delete znData;
    znData = new QList<LocalZeroNodes>();
    std::copy(zeroNodeSettings.begin(), zeroNodeSettings.end(), std::back_inserter(*znData));

    updateAllLZNData();
}

void LocalZNTableModel::sortZNData(QList<LocalZeroNodes>* list) {

  struct {
      bool operator()(LocalZeroNodes a, LocalZeroNodes b) const {
          return a.alias < b.alias;
      }
  } lznSort;

  std::sort(list->begin(), list->end(), lznSort);

}




// void LocalZNTableModel::setupZeroNode(MainWindow* main, Ui_znsetup* zn, QDialog* d, const LocalZeroNodes &lineNode) {
//
//     int portIndex = lineNode.ipAddress.lastIndexOf(":");
//     zn->txtZNAlias->setText(lineNode.alias);
//     zn->txtZNIpAddress->setText(lineNode.ipAddress.left(portIndex));
//     zn->txtZNPort->setText(QString::number(23801));
//     zn->txtZNPrivateKey->setText(lineNode.privateKey);
//     zn->txtZNOutput->setText(lineNode.txid);
//     if (lineNode.txid.length() > 0) {
//         zn->txtZNIndex->setText(QString::number(lineNode.index));
//     } else {
//         zn->txtZNIndex->setText(QString::number(0));
//     }
//
//     QObject::connect(zn->btnZNNewPrivKey, &QPushButton::clicked, [=] () {
//         main->getRPC()->getZNPrivateKey(zn);
//     });
//
//     QObject::connect(zn->btnZNGetOutput, &QPushButton::clicked, [=] () {
//
//         if (outputs == nullptr)
//             outputs = new QList<ZNOutputs>;
//
//         if (znData == nullptr)
//             znData = new QList<LocalZeroNodes>;
//
//         main->getRPC()->getZNOutputs(zn, outputs, znData);
//
//     });
//
//     QObject::connect(zn->btnZNUpdate, &QPushButton::clicked, [=] () {
//         bool ok = false;
//         int index = zn->txtZNIndex->text().QString::toLongLong(&ok);
//
//         if (zn->txtZNAlias->text().length() > 0 &&
//             zn->txtZNIpAddress->text().length() > 0 &&
//             zn->txtZNPort->text().length() > 0 &&
//             zn->txtZNPrivateKey->text().length() > 0 &&
//             zn->txtZNOutput->text().length() > 0 &&
//             ok) {
//
//             LocalZeroNodes newNode{
//               "RESTART",
//               zn->txtZNAlias->text(),
//               zn->txtZNIpAddress->text() + ":" + zn->txtZNPort->text(),
//               zn->txtZNPrivateKey->text(),
//               zn->txtZNOutput->text(),
//               index
//             };
//
//             if (lineNode.alias.length() == 0) {
//                 zeroNodeSettings.push_back(newNode);
//                 addLocalZNData();
//                 writeZeroNodeSetup();
//             } else {
//                 updateZeroNodeSetup(lineNode, newNode);
//             }
//
//             d->accept();
//         }
//     });
//
//     QObject::connect(zn->btnZNUpdateClose, &QPushButton::clicked, [=] () {
//         d->reject();
//     });
//
// }

// void LocalZNTableModel::deleteZeroNodeFromSetup(const LocalZeroNodes &delNode) {
//
//   QList<LocalZeroNodes> newZeroNodeList = zeroNodeSettings;
//   zeroNodeSettings.clear();
//
//   for(auto& it : newZeroNodeList) {
//       if (!(delNode.status == it.status &&
//           delNode.alias == it.alias &&
//           delNode.ipAddress == it.ipAddress &&
//           delNode.privateKey == it.privateKey &&
//           delNode.txid == it.txid &&
//           delNode.index == it.index)) {
//           zeroNodeSettings.push_back(it);
//       }
//   }
//
//   //Update Ui
//   addLocalZNData();
//   writeZeroNodeSetup();
//
// }

// void LocalZNTableModel::writeZeroNodeSetup() {
//
//     QList<QString> zeroNodes;
//     for(auto& it : zeroNodeSettings) {
//         QString zeroNode = it.alias + " " + it.ipAddress + " " + it.privateKey + " " + it.txid + " " + QString::number(it.index);
//         zeroNodes.push_back(zeroNode);
//     }
//
//     // QString confLocation = Settings::getInstance()->zeroNodeConfWritableLocation();
//     // Settings::getInstance()->updateToZeroNodeConf(confLocation, zeroNodes);
//
// }

// void LocalZNTableModel::updateZeroNodeSetup(const LocalZeroNodes &lineNode, LocalZeroNodes &updatedNode) {
//     QList<LocalZeroNodes> newZeroNodeList = zeroNodeSettings;
//     zeroNodeSettings.clear();
//
//     for(auto& it : newZeroNodeList) {
//         if (!(lineNode.status == it.status &&
//             lineNode.alias == it.alias &&
//             lineNode.ipAddress == it.ipAddress &&
//             lineNode.privateKey == it.privateKey &&
//             lineNode.txid == it.txid &&
//             lineNode.index == it.index)) {
//             zeroNodeSettings.push_back(it);
//         } else {
//             zeroNodeSettings.push_back(updatedNode);
//         }
//     }
//
//     //Update Ui
//     addLocalZNData();
//     writeZeroNodeSetup();
// }

// void LocalZNTableModel::updateZNPrivKeySetup(Ui_znsetup* zn, QString* newKey) {
//     zn->txtZNPrivateKey->setText(*newKey);
// }

// void LocalZNTableModel::updateZNOutput(Ui_znsetup* zn) {
//     if (!outputs->empty()) {
//           if (outputIndex + 1 >= outputs->length()) {
//             outputIndex = 0;
//           } else {
//             outputIndex++;
//           }
//           zn->txtZNOutput->setText(outputs->at(outputIndex).txid);
//           zn->txtZNIndex->setText(QString::number(outputs->at(outputIndex).index));
//     }
// }

bool LocalZNTableModel::isLocal(QString txid) {

  QList<LocalZeroNodes>::iterator i;
  for (i = modeldata->begin(); i != modeldata->end(); ++i) {
      LocalZeroNodes lzn = *i;
      if (txid == lzn.txid)
          return true;
  }

  return false;

}



void LocalZNTableModel::updateAllLZNData() {
    auto newmodeldata = new QList<LocalZeroNodes>();

    if (znData != nullptr) std::copy(znData->begin(), znData->end(), std::back_inserter(*newmodeldata));

    // Sort by reverse time
    sortZNData(newmodeldata);

    // And then swap out the modeldata with the new one.
    delete modeldata;
    modeldata = newmodeldata;

    dataChanged(index(0, 0), index(modeldata->size()-1, columnCount(index(0,0))-1));
    layoutChanged();
}


 int LocalZNTableModel::rowCount(const QModelIndex&) const
 {
    if (modeldata == nullptr) return 0;
    return modeldata->size();
 }

 int LocalZNTableModel::columnCount(const QModelIndex&) const
 {
    return headers.size();
 }


 QVariant LocalZNTableModel::data(const QModelIndex &index, int role) const
 {
     // Align column 4,5 (confirmations, amount) right
    if (role == Qt::TextAlignmentRole)
        return QVariant(Qt::AlignVCenter);

    auto dat = modeldata->at(index.row());

    // if (role == Qt::ForegroundRole) {
    //     // if (dat.confirmations <= 0) {
    //     //     QBrush b;
    //     //     b.setColor(Qt::red);
    //     //     return b;
    //     // }
    //
    //     // Else, just return the default brush
    //     QBrush b;
    //     b.setColor(Qt::black);
    //     return b;
    // }

    if (role == Qt::DisplayRole) {
        switch (index.column()) {
        case 0: return dat.status;
        case 1: return dat.alias;
        case 2: return dat.ipAddress;
        case 3: return dat.privateKey;
        case 4: return dat.txid;
        case 5: return dat.index;
        }
    }

    return QVariant();
 }


 QVariant LocalZNTableModel::headerData(int section, Qt::Orientation orientation, int role) const
 {
     if (role == Qt::TextAlignmentRole)
        return QVariant(Qt::AlignCenter);

     if (role == Qt::FontRole) {
         QFont f;
         f.setBold(true);
         return f;
     }

     if (role == Qt::DisplayRole && orientation == Qt::Horizontal) {
         return headers.at(section);
     }

     return QVariant();
 }

QString LocalZNTableModel::getLZNStatus(int row) const {
    return modeldata->at(row).status;
}

QString LocalZNTableModel::getLZNAlias(int row) const {
    return modeldata->at(row).alias;
}

QString LocalZNTableModel::getLZNIpAddress(int row) const {
    return modeldata->at(row).ipAddress;
}

QString LocalZNTableModel::getLZNPrivateKey(int row) const {
    return modeldata->at(row).privateKey;
}

QString LocalZNTableModel::getLZNTxid(int row) const {
    return modeldata->at(row).txid;
}

QString LocalZNTableModel::getLZNIndex(int row) const {
    return modeldata->at(row).index;
}










GlobalZNTableModel::GlobalZNTableModel(CWallet *_wallet, QObject *parent) :
    QAbstractTableModel(parent),
    wallet(_wallet)
{
    headers << QObject::tr("Rank") << QObject::tr("Address") << QObject::tr("Version")
            << QObject::tr("Status") << QObject::tr("Active") << QObject::tr("Last Seen")
            << QObject::tr("Last Paid") << QObject::tr("Txid") << QObject::tr("IP Address");
}

GlobalZNTableModel::~GlobalZNTableModel() {
    delete modeldata;
    delete znData;
}



void GlobalZNTableModel::refreshGlobalZNData(LocalZNTableModel *lzn) {
    delete znData;
    znData = new QList<GlobalZeroNodes>();

    std::vector<pair<int, CZeronode> > vZeronodeRanks = znodeman.GetZeronodeRanks(chainActive.Tip()->nHeight);
    BOOST_FOREACH (PAIRTYPE(int, CZeronode) & s, vZeronodeRanks) {
        std::string strVin = s.second.vin.prevout.ToStringShort();
        std::string strTxHash = s.second.vin.prevout.hash.ToString();
        uint32_t oIdx = s.second.vin.prevout.n;

        CZeronode* zn = znodeman.Find(s.second.vin);

        GlobalZeroNodes newGZNode;

        if (zn != NULL) {

            std::string strStatus = zn->Status();
            std::string strHost;
            int port;
            SplitHostPort(zn->addr.ToString(), port, strHost);
            CNetAddr node = CNetAddr(strHost, false);
            std::string strNetwork = GetNetworkName(node.GetNetwork());

            newGZNode.rank = strStatus == "ENABLED" ? s.first : 0;
            newGZNode.address = QString::fromStdString(EncodeDestination(zn->pubKeyCollateralAddress.GetID()));
            newGZNode.version = zn->protocolVersion;
            newGZNode.status = QString::fromStdString(strStatus);
            newGZNode.active  = (qint64)(zn->lastPing.sigTime - zn->sigTime);
            newGZNode.lastSeen = QString::number(zn->lastPing.sigTime);
            newGZNode.lastPaid = QString::number(zn->GetLastPaid());
            newGZNode.txid = QString::fromStdString(strTxHash);
            newGZNode.ipAddress = QString::fromStdString(strHost);
            newGZNode.local = false;

            if (lzn->isLocal(QString::fromStdString(strTxHash))) {
                newGZNode.local = true;
            } else {
                newGZNode.local = false;
            }

            znData->append(newGZNode);
        }
    }

    updateAllZNData();
}

void GlobalZNTableModel::sortZNData(QList<GlobalZeroNodes>* list) {

  struct {
      bool operator()(GlobalZeroNodes a, GlobalZeroNodes b) const {
        if (a.local != b.local)
            return a.local > b.local;

        return a.rank < b.rank; // reverse sor
      }
  } gznSort;

  std::sort(list->begin(), list->end(), gznSort);

}

void GlobalZNTableModel::updateAllZNData() {
    auto newmodeldata = new QList<GlobalZeroNodes>();

    if (znData != nullptr) std::copy(znData->begin(), znData->end(), std::back_inserter(*newmodeldata));

    // Sort by reverse time
    sortZNData(newmodeldata);

    // And then swap out the modeldata with the new one.
    delete modeldata;
    modeldata = newmodeldata;

    dataChanged(index(0, 0), index(modeldata->size()-1, columnCount(index(0,0))-1));
    layoutChanged();
}

 int GlobalZNTableModel::rowCount(const QModelIndex&) const
 {
    if (modeldata == nullptr) return 0;
    return modeldata->size();
 }

 int GlobalZNTableModel::columnCount(const QModelIndex&) const
 {
    return headers.size();
 }


 QVariant GlobalZNTableModel::data(const QModelIndex &index, int role) const
 {
     // Align column 4,5 (confirmations, amount) right
    if (role == Qt::TextAlignmentRole)
        return QVariant(Qt::AlignVCenter);

    auto dat = modeldata->at(index.row());

    if (role == Qt::DisplayRole) {

        QDateTime myDateTime;


        switch (index.column()) {
        case 0: return dat.rank;
        case 1: return dat.address;
        case 2: return dat.version;
        case 3: return dat.status;
        case 4: return convertSecondsToDays(dat.active);
        case 5: return dat.lastSeen;
        case 6: return dat.lastPaid;
        case 7: return dat.txid;
        case 8: return dat.ipAddress;
        }
    }

    return QVariant();
 }


 QVariant GlobalZNTableModel::headerData(int section, Qt::Orientation orientation, int role) const
 {
     if (role == Qt::TextAlignmentRole)
        return QVariant(Qt::AlignCenter);

     if (role == Qt::FontRole) {
         QFont f;
         f.setBold(true);
         return f;
     }

     if (role == Qt::DisplayRole && orientation == Qt::Horizontal) {
         return headers.at(section);
     }

     return QVariant();
 }

int GlobalZNTableModel::getGZNRank(int row) const {
    return modeldata->at(row).rank;
}

QString GlobalZNTableModel::getGZNAddr(int row) const {
    return modeldata->at(row).address;
}

int GlobalZNTableModel::getGZNVersion(int row) const {
    return modeldata->at(row).version;
}

QString GlobalZNTableModel::getGZNStatus(int row) const {
    return modeldata->at(row).status;
}

int GlobalZNTableModel::getGZNActive(int row) const {
    return modeldata->at(row).active;
}

QString GlobalZNTableModel::getGZNLastSeen(int row) const {
    return modeldata->at(row).lastSeen;
}

QString GlobalZNTableModel::getGZNLastPaid(int row) const {
    return modeldata->at(row).lastPaid;
}

QString GlobalZNTableModel::getGZNTxid(int row) const {
    return modeldata->at(row).txid;
}

QString GlobalZNTableModel::getGZNIp(int row) const {
    return modeldata->at(row).ipAddress;
}
