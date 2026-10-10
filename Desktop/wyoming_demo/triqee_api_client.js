/**
 * Triqee Client API Bridge (v0.1.0)
 * =================================
 * Standard JavaScript fetch wrapper to submit form registrations
 * and query geodesic/latency calculations from the FastAPI backend.
 */

class TriqeeAPIClient {
  constructor(baseUrl = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  /**
   * Check backend health status
   */
  async checkHealth() {
    try {
      const res = await fetch(`${this.baseUrl}/health`);
      return await res.json();
    } catch (err) {
      console.error("[TriqeeAPI] Health check failed:", err);
      return { status: "offline", error: err.message };
    }
  }

  /**
   * Register a new developer, quant, or community lead
   * @param {Object} payload { tier, email, identifier, allocated_tq, wallet_address }
   */
  async registerLead(payload) {
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/leads/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Registration failed");
      }
      return { success: true, data };
    } catch (err) {
      console.error("[TriqeeAPI] Registration error:", err);
      return { success: false, error: err.message };
    }
  }

  /**
   * Compute geodesic distance between two points
   */
  async computeDistance(lat1, lon1, lat2, lon2) {
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/geodesic/distance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat1, lon1, lat2, lon2 })
      });
      return await res.json();
    } catch (err) {
      console.error("[TriqeeAPI] Distance calculation error:", err);
      return { error: err.message };
    }
  }

  /**
   * Classify an inbound message
   */
  async classifyInquiry(userHandle, messageText, platform = "Web") {
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/triage/classify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_handle: userHandle, message_text: messageText, platform })
      });
      return await res.json();
    } catch (err) {
      console.error("[TriqeeAPI] Triage error:", err);
      return { error: err.message };
    }
  }
}

// Attach to window if running in browser
if (typeof window !== "undefined") {
  window.TriqeeAPIClient = TriqeeAPIClient;
}
