class RetryService {
  constructor(options = {}) {
    this.maxRetries = options.maxRetries || 3
    this.initialDelay = options.initialDelay || 1000
    this.maxDelay = options.maxDelay || 30000
    this.backoffMultiplier = options.backoffMultiplier || 2
    this.jitter = options.jitter || true
  }

  calculateDelay(attempt) {
    let delay = Math.min(
      this.initialDelay * Math.pow(this.backoffMultiplier, attempt),
      this.maxDelay
    )

    if (this.jitter) {
      delay = delay * (0.5 + Math.random() * 0.5)
    }

    return Math.floor(delay)
  }

  async withRetry(fn, context = {}) {
    let lastError

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        return await fn({ attempt, context })
      } catch (error) {
        lastError = error
        console.log(`Attempt ${attempt + 1} failed: ${error.message}`)

        if (attempt < this.maxRetries) {
          const delay = this.calculateDelay(attempt)
          console.log(`Retrying in ${delay}ms...`)
          await this.sleep(delay)
        }
      }
    }

    throw new Error(`All ${this.maxRetries + 1} attempts failed. Last error: ${lastError.message}`)
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  // Create a retrying message handler
  createRetryHandler(handler, dlqHandler, options = {}) {
    return async (message) => {
      return this.withRetry(
        async ({ attempt }) => {
          return await handler(message)
        },
        { dlqHandler, message, ...options }
      )
    }
  }
}

module.exports = RetryService
