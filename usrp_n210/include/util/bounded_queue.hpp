#pragma once
#include <condition_variable>
#include <cstddef>
#include <deque>
#include <mutex>
#include <optional>



namespace util {

// A simple bounded blocking queue.
// - push() blocks when full
// - pop() blocks when empty
// - close() wakes all waiters; pop() returns nullopt when closed+empty
template <typename T>
class BoundedQueue {
public:
    explicit BoundedQueue(size_t capacity) : capacity_(capacity) {}

    void close() {
        std::lock_guard<std::mutex> lk(m_);
        closed_ = true;
        cv_not_empty_.notify_all();
        cv_not_full_.notify_all();
    }

    bool closed() const {
        std::lock_guard<std::mutex> lk(m_);
        return closed_;
    }

    // Returns false if queue is closed (i.e., item not accepted)
    template <class U>
    bool push(U&& item) {
        std::unique_lock<std::mutex> lk(m_);
        cv_not_full_.wait(lk, [&] { return closed_ || q_.size() < capacity_; });
        if (closed_) return false;
        q_.push_back(std::forward<U>(item));
        cv_not_empty_.notify_one();
        return true;
    }

    // Returns nullopt if closed and empty
    std::optional<T> pop() {
        std::unique_lock<std::mutex> lk(m_);
        cv_not_empty_.wait(lk, [&] { return closed_ || !q_.empty(); });
        if (q_.empty()) return std::nullopt;
        T item = std::move(q_.front());
        q_.pop_front();
        cv_not_full_.notify_one();
        return item;
    }

    size_t size() const {
        std::lock_guard<std::mutex> lk(m_);
        return q_.size();
    }

private:
    const size_t capacity_;
    mutable std::mutex m_;
    std::condition_variable cv_not_empty_;
    std::condition_variable cv_not_full_;
    std::deque<T> q_;
    bool closed_ = false;
};

} // namespace util
