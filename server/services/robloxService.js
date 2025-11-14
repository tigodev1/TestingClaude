const axios = require('axios');

const ROBLOX_API_BASE = 'https://apis.roblox.com/cloud/v2';

class RobloxService {
  constructor() {
    this.apiKey = process.env.ROBLOX_API_KEY;
    this.universeId = process.env.UNIVERSE_ID;

    if (!this.apiKey) {
      console.warn('⚠️  ROBLOX_API_KEY not set in .env file');
    }
    if (!this.universeId) {
      console.warn('⚠️  UNIVERSE_ID not set in .env file');
    }
  }

  async makeRequest(endpoint) {
    if (!this.apiKey) {
      throw new Error('ROBLOX_API_KEY not configured. Please set it in your .env file');
    }

    try {
      const response = await axios.get(`${ROBLOX_API_BASE}${endpoint}`, {
        headers: {
          'x-api-key': this.apiKey,
          'Content-Type': 'application/json'
        }
      });
      return response.data;
    } catch (error) {
      if (error.response) {
        throw new Error(`Roblox API Error: ${error.response.status} - ${JSON.stringify(error.response.data)}`);
      }
      throw error;
    }
  }

  async getUniverse() {
    if (!this.universeId) {
      throw new Error('UNIVERSE_ID not configured. Please set it in your .env file');
    }

    const data = await this.makeRequest(`/universes/${this.universeId}`);

    // Extract root place ID from the rootPlace path
    let rootPlaceId = null;
    if (data.rootPlace) {
      const match = data.rootPlace.match(/places\/(\d+)/);
      if (match) {
        rootPlaceId = match[1];
      }
    }

    return {
      ...data,
      rootPlaceId,
      timestamp: new Date().toISOString()
    };
  }

  async getPlace(placeId) {
    const data = await this.makeRequest(`/places/${placeId}`);
    return {
      ...data,
      timestamp: new Date().toISOString()
    };
  }

  async listPlaceChildren(universeId, placeId, instanceId = 'root') {
    const data = await this.makeRequest(
      `/universes/${universeId}/places/${placeId}/instances/${instanceId}:listChildren`
    );
    return data;
  }

  async getInstance(universeId, placeId, instanceId) {
    const data = await this.makeRequest(
      `/universes/${universeId}/places/${placeId}/instances/${instanceId}`
    );
    return data;
  }
}

module.exports = new RobloxService();
