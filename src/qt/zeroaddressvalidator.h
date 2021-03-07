// Copyright (c) 2011-2014 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#ifndef ZERO_QT_ZEROADDRESSVALIDATOR_H
#define ZERO_QT_ZEROADDRESSVALIDATOR_H

#include <QValidator>

/** Base58 entry widget validator, checks for valid characters and
 * removes some whitespace.
 */
class ZeroAddressEntryValidator : public QValidator
{
    Q_OBJECT

public:
    explicit ZeroAddressEntryValidator(QObject *parent, bool allowZAddresses = false);

    State validate(QString &input, int &pos) const;
private:
    bool _allowZAddresses;
};

/** Zero address widget validator, checks for a valid zero address.
 */
class ZeroAddressCheckValidator : public QValidator
{
    Q_OBJECT

public:
    explicit ZeroAddressCheckValidator(QObject *parent, bool allowZAddresses = false);

    State validate(QString &input, int &pos) const;
private:
    bool _allowZAddresses;
};

#endif // ZERO_QT_ZEROADDRESSVALIDATOR_H
