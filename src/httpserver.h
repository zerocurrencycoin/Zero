// Copyright (c) 2015 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php .

#ifndef BITCOIN_HTTPSERVER_H
#define BITCOIN_HTTPSERVER_H

#include <string>
#include <stdint.h>
#include <boost/thread.hpp>
#include <boost/scoped_ptr.hpp>
#include <boost/function.hpp>

//! Zero's hottest RPC, getalldata, serialises itself behind an in-flight gate
//! (wallet/rpczerowallet.cpp), returning RPC_DATA_CONTINUE (-34) rather than
//! running concurrently. Extra HTTP workers cannot parallelise it, so the
//! requirement is headroom for a cheap call while an expensive one holds the
//! gate -- not a large pool. Both are runtime-tunable: -rpcthreads,
//! -rpcworkqueue.
//!
//! Upstream history: 4 threads dates from Bitcoin 2013 (21eb5adadb), a queue
//! of 16 from 2015 (40b556d374). Bitcoin raised them to 16/64 in 2024
//! (e56fc7ce6a, bitcoin#29386) for its own RPC load; Zero's consumers are a
//! wallet UI and an explorer, so that reasoning does not carry over.
static const int DEFAULT_HTTP_THREADS=4;
static const int DEFAULT_HTTP_WORKQUEUE=4;
static const int DEFAULT_HTTP_SERVER_TIMEOUT=30;

struct evhttp_request;
struct event_base;
class CService;
class HTTPRequest;

/** Initialize HTTP server.
 * Call this before RegisterHTTPHandler or EventBase().
 */
bool InitHTTPServer();
/** Start HTTP server.
 * This is separate from InitHTTPServer to give users race-condition-free time
 * to register their handlers between InitHTTPServer and StartHTTPServer.
 */
bool StartHTTPServer();
/** Interrupt HTTP server threads */
void InterruptHTTPServer();
/** Stop HTTP server */
void StopHTTPServer();

/** Handler for requests to a certain HTTP path */
typedef boost::function<void(HTTPRequest* req, const std::string &)> HTTPRequestHandler;
/** Register handler for prefix.
 * If multiple handlers match a prefix, the first-registered one will
 * be invoked.
 */
void RegisterHTTPHandler(const std::string &prefix, bool exactMatch, const HTTPRequestHandler &handler);
/** Unregister handler for prefix */
void UnregisterHTTPHandler(const std::string &prefix, bool exactMatch);

/** Return evhttp event base. This can be used by submodules to
 * queue timers or custom events.
 */
struct event_base* EventBase();

/** In-flight HTTP request.
 * Thin C++ wrapper around evhttp_request.
 */
class HTTPRequest
{
private:
    struct evhttp_request* req;

    // For test access
protected:
    bool replySent;

public:
    HTTPRequest(struct evhttp_request* req);
    virtual ~HTTPRequest();

    enum RequestMethod {
        UNKNOWN,
        GET,
        POST,
        HEAD,
        PUT
    };

    /** Get requested URI.
     */
    std::string GetURI();

    /** Get CService (address:ip) for the origin of the http request.
     */
    virtual CService GetPeer();

    /** Get request method.
     */
    virtual RequestMethod GetRequestMethod();

    /**
     * Get the request header specified by hdr, or an empty string.
     * Return an pair (isPresent,string).
     */
    virtual std::pair<bool, std::string> GetHeader(const std::string& hdr);

    /**
     * Read request body.
     *
     * @note As this consumes the underlying buffer, call this only once.
     * Repeated calls will return an empty string.
     */
    std::string ReadBody();

    /**
     * Write output header.
     *
     * @note call this before calling WriteErrorReply or Reply.
     */
    virtual void WriteHeader(const std::string& hdr, const std::string& value);

    /**
     * Write HTTP reply.
     * nStatus is the HTTP status code to send.
     * strReply is the body of the reply. Keep it empty to send a standard message.
     *
     * @note Can be called only once. As this will give the request back to the
     * main thread, do not call any other HTTPRequest methods after calling this.
     */
    virtual void WriteReply(int nStatus, const std::string& strReply = "");
};

/** Event handler closure.
 */
class HTTPClosure
{
public:
    virtual void operator()() = 0;
    virtual ~HTTPClosure() {}
};

/** Event class. This can be used either as an cross-thread trigger or as a timer.
 */
class HTTPEvent
{
public:
    /** Create a new event.
     * deleteWhenTriggered deletes this event object after the event is triggered (and the handler called)
     * handler is the handler to call when the event is triggered.
     */
    HTTPEvent(struct event_base* base, bool deleteWhenTriggered, const boost::function<void(void)>& handler);
    ~HTTPEvent();

    /** Trigger the event. If tv is 0, trigger it immediately. Otherwise trigger it after
     * the given time has elapsed.
     */
    void trigger(struct timeval* tv);

    bool deleteWhenTriggered;
    boost::function<void(void)> handler;
private:
    struct event* ev;
};

#endif // BITCOIN_HTTPSERVER_H
