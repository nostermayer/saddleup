/**
 * Jest setup file for frontend tests
 * Configures global mocks and test utilities
 */

// Mock global objects that don't exist in Node.js environment
global.WebSocket = class MockWebSocket {
  constructor() {
    this.CONNECTING = 0;
    this.OPEN = 1;
    this.CLOSING = 2;
    this.CLOSED = 3;
  }
};

global.WebSocket.CONNECTING = 0;
global.WebSocket.OPEN = 1;
global.WebSocket.CLOSING = 2;
global.WebSocket.CLOSED = 3;

// Mock localStorage
global.localStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};

// Mock sessionStorage
global.sessionStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};

// Mock window.location
delete global.window;
global.window = {
  location: {
    href: 'http://localhost:8080',
    hostname: 'localhost',
    protocol: 'http:',
    search: '',
    pathname: '/'
  },
  addEventListener: jest.fn(),
  removeEventListener: jest.fn()
};

// Mock document
global.document = {
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  getElementById: jest.fn(),
  querySelector: jest.fn(),
  querySelectorAll: jest.fn(() => []),
  createElement: jest.fn(() => ({
    classList: {
      add: jest.fn(),
      remove: jest.fn(),
      contains: jest.fn(),
      toggle: jest.fn()
    },
    addEventListener: jest.fn(),
    appendChild: jest.fn(),
    removeChild: jest.fn(),
    style: {},
    dataset: {},
    textContent: '',
    innerHTML: ''
  })),
  body: {
    appendChild: jest.fn(),
    removeChild: jest.fn()
  }
};

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  log: jest.fn(),
  error: jest.fn(),
  warn: jest.fn(),
  info: jest.fn(),
  debug: jest.fn()
};

// Mock timer functions
global.setTimeout = jest.fn((fn) => fn());
global.setInterval = jest.fn();
global.clearTimeout = jest.fn();
global.clearInterval = jest.fn();

// Mock Math.random for predictable tests
const mockMath = Object.create(global.Math);
mockMath.random = jest.fn(() => 0.5);
global.Math = mockMath;

// Mock Date for predictable tests
global.Date = {
  ...Date,
  now: jest.fn(() => 1234567890000)
};

// Clean up after each test
afterEach(() => {
  jest.clearAllMocks();
});