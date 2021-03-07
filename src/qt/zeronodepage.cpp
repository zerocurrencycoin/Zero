// Copyright (c) 2021 Team Zero developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.


#include "zeronodepage.h"
#include "ui_zeronodepage.h"

#include "zeronodetablemodel.h"
#include "zeronodesetup.h"
#include "platformstyle.h"
#include "guiutil.h"

#include <QMenu>

ZeroNodePage::ZeroNodePage(const PlatformStyle *_platformStyle, QWidget *parent) :
    QDialog(parent),
    platformStyle(_platformStyle),
    ui(new Ui::ZeroNodePage),
    gzModel(0),
    lzModel(0)
{
    ui->setupUi(this);

    // Context menu actions
    startAction = new QAction(tr("&Start"), this);
    enableAction = new QAction(tr("&Enable"), this);
    disableAction = new QAction(tr("Disable"), this);
    editAction = new QAction(tr("&Edit"), this);
    deleteAction = new QAction(tr("&Delete"), this);

    // Build context menu
    contextMenu = new QMenu(this);
    contextMenu->addAction(startAction);
    contextMenu->addAction(enableAction);
    contextMenu->addAction(disableAction);
    contextMenu->addAction(editAction);
    contextMenu->addAction(deleteAction);

    //connect actions
    connect(editAction, SIGNAL(triggered()), this, SLOT(editZeroNode()));

    connect(ui->tableZeroNodeLocal, SIGNAL(customContextMenuRequested(QPoint)), this, SLOT(contextualMenu(QPoint)));

}

ZeroNodePage::~ZeroNodePage()
{
    delete ui;
}

void ZeroNodePage::setGlobalModel(GlobalZNTableModel *_model) {

    this->gzModel = _model;
    if(!_model)
        return;

    ui->tableZeroNodeGlobal->setModel(_model);

    ui->tableZeroNodeGlobal->horizontalHeader()->setSectionResizeMode(0, QHeaderView::ResizeToContents);
    ui->tableZeroNodeGlobal->horizontalHeader()->setSectionResizeMode(1, QHeaderView::ResizeToContents);
    ui->tableZeroNodeGlobal->horizontalHeader()->setSectionResizeMode(2, QHeaderView::ResizeToContents);
    ui->tableZeroNodeGlobal->horizontalHeader()->setSectionResizeMode(3, QHeaderView::ResizeToContents);
    ui->tableZeroNodeGlobal->horizontalHeader()->setSectionResizeMode(4, QHeaderView::ResizeToContents);
    ui->tableZeroNodeGlobal->horizontalHeader()->setSectionResizeMode(5, QHeaderView::ResizeToContents);
    ui->tableZeroNodeGlobal->horizontalHeader()->setSectionResizeMode(6, QHeaderView::ResizeToContents);
    ui->tableZeroNodeGlobal->horizontalHeader()->setSectionResizeMode(7, QHeaderView::ResizeToContents);
    ui->tableZeroNodeGlobal->horizontalHeader()->setSectionResizeMode(8, QHeaderView::Stretch);
}

void ZeroNodePage::setLocalModel(LocalZNTableModel *_model) {

    this->lzModel = _model;
    if(!_model)
        return;

    ui->tableZeroNodeLocal->setModel(_model);

    ui->tableZeroNodeLocal->horizontalHeader()->setSectionResizeMode(0, QHeaderView::ResizeToContents);
    ui->tableZeroNodeLocal->horizontalHeader()->setSectionResizeMode(1, QHeaderView::ResizeToContents);
    ui->tableZeroNodeLocal->horizontalHeader()->setSectionResizeMode(2, QHeaderView::ResizeToContents);
    ui->tableZeroNodeLocal->horizontalHeader()->setSectionResizeMode(3, QHeaderView::ResizeToContents);
    ui->tableZeroNodeLocal->horizontalHeader()->setSectionResizeMode(4, QHeaderView::ResizeToContents);
    ui->tableZeroNodeLocal->horizontalHeader()->setSectionResizeMode(5, QHeaderView::Stretch);

    connect(ui->tableZeroNodeLocal->selectionModel(), SIGNAL(selectionChanged(QItemSelection,QItemSelection)),
        this, SLOT(selectionChanged()));
}

void ZeroNodePage::editZeroNode() {

    // QModelIndex index = ui->tableZeroNodeLocal->indexAt(pos);
    // if (index.row() < 0) return;

    int row = index.row();

    LocalZeroNodes lineNode {
        ui->tableZeroNodeLocal->model()->data(index.sibling(index.row(), 0)).toString(),
        ui->tableZeroNodeLocal->model()->data(index.sibling(index.row(), 1)).toString(),
        ui->tableZeroNodeLocal->model()->data(index.sibling(index.row(), 2)).toString(),
        ui->tableZeroNodeLocal->model()->data(index.sibling(index.row(), 3)).toString(),
        ui->tableZeroNodeLocal->model()->data(index.sibling(index.row(), 4)).toString(),
        ui->tableZeroNodeLocal->model()->data(index.sibling(index.row(), 5)).toString()
    };

    ZeroNodeSetup dlg(platformStyle, this);
    dlg.setAlias(lineNode.alias);
    dlg.setIpAddress(lineNode.ipAddress);
    dlg.setPrivateKey(lineNode.privateKey);
    dlg.setOutput(lineNode.txid);
    dlg.setIndex(lineNode.index);
    dlg.exec();

}

void ZeroNodePage::selectionChanged()
{
    // Set button states based on selected tab and selection
    QModelIndexList selection = GUIUtil::getEntryData(ui->tableZeroNodeLocal, 0);
    if(!selection.isEmpty()) {
        QString status = selection.at(0).data(0).toString();
        if (status == "ENABLED") {
              disableAction->setEnabled(true);
              enableAction->setEnabled(false);
          } else {
              disableAction->setEnabled(false);
              enableAction->setEnabled(true);
        }
    }
}

void ZeroNodePage::contextualMenu(const QPoint &point)
{
    index = ui->tableZeroNodeLocal->indexAt(point);
    if(index.isValid())
    {

        contextMenu->exec(QCursor::pos());
    }
}
