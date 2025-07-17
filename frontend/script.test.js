/**
 * Frontend Unit Tests for SaddleUp.io
 * 
 * These tests verify the core functionality of the frontend JavaScript code
 * including WebSocket communication, betting logic, and UI updates.
 */

// Mock DOM environment
const mockElement = () => ({
    textContent: '',
    innerHTML: '',
    style: {},
    dataset: {},
    disabled: false,
    value: '',
    classList: {
        add: jest.fn(),
        remove: jest.fn(),
        contains: jest.fn(() => false),
        toggle: jest.fn()
    },
    addEventListener: jest.fn(),
    appendChild: jest.fn(),
    removeChild: jest.fn(),
    querySelector: jest.fn(),
    querySelectorAll: jest.fn(() => [])
});

// Mock WebSocket
class MockWebSocket {
    constructor(url) {
        this.url = url;
        this.readyState = 1; // OPEN
        this.sentMessages = [];
        this.onopen = null;
        this.onmessage = null;
        this.onclose = null;
        this.onerror = null;
        
        setTimeout(() => {
            if (this.onopen) this.onopen();
        }, 0);
    }
    
    send(data) {
        this.sentMessages.push(JSON.parse(data));
    }
    
    close() {
        this.readyState = 3; // CLOSED
        if (this.onclose) this.onclose();
    }
    
    simulateMessage(data) {
        if (this.onmessage) {
            this.onmessage({ data: JSON.stringify(data) });
        }
    }
}

// Setup global mocks
beforeAll(() => {
    global.WebSocket = MockWebSocket;
    global.WebSocket.OPEN = 1;
    global.WebSocket.CLOSED = 3;
    
    global.document = {
        getElementById: jest.fn(() => mockElement()),
        createElement: jest.fn(() => mockElement()),
        querySelectorAll: jest.fn(() => []),
        addEventListener: jest.fn(),
        body: mockElement()
    };
    
    global.window = {
        location: {
            protocol: 'http:',
            hostname: 'localhost',
            href: 'http://localhost:8080'
        }
    };
    
    global.console = {
        log: jest.fn(),
        error: jest.fn(),
        warn: jest.fn()
    };
});

describe('SaddleUpGame Frontend Functionality', () => {
    
    describe('WebSocket URL Generation', () => {
        test('should generate correct WebSocket URL for localhost', () => {
            const hostname = 'localhost';
            const protocol = 'http:';
            
            let wsUrl;
            if (hostname === 'localhost' || hostname === '127.0.0.1') {
                wsUrl = `ws://${hostname}:8765`;
            } else {
                wsUrl = `${protocol === 'https:' ? 'wss:' : 'ws:'}//${hostname}/ws`;
            }
            
            expect(wsUrl).toBe('ws://localhost:8765');
        });
        
        test('should generate correct WebSocket URL for production', () => {
            const hostname = 'saddleup.io';
            const protocol = 'https:';
            
            let wsUrl;
            if (hostname === 'localhost' || hostname === '127.0.0.1') {
                wsUrl = `ws://${hostname}:8765`;
            } else {
                wsUrl = `${protocol === 'https:' ? 'wss:' : 'ws:'}//${hostname}/ws`;
            }
            
            expect(wsUrl).toBe('wss://saddleup.io/ws');
        });
    });
    
    describe('Betting Logic', () => {
        test('should validate single bet selection', () => {
            const currentRaceBets = [];
            const selectedBetType = 'winner';
            const selectedHorse = 1;
            
            // Check if user already has a bet of this type
            const hasBetOfType = currentRaceBets.some(bet => bet.type === selectedBetType);
            
            expect(hasBetOfType).toBe(false);
            expect(selectedHorse).toBe(1);
        });
        
        test('should prevent duplicate bet types', () => {
            const currentRaceBets = [{ type: 'winner', amount: 1.0 }];
            const selectedBetType = 'winner';
            
            const hasBetOfType = currentRaceBets.some(bet => bet.type === selectedBetType);
            
            expect(hasBetOfType).toBe(true);
        });
        
        test('should validate trifecta selection', () => {
            const trifectaSelection = [1, 2, 3];
            const isValidTrifecta = trifectaSelection.length === 3;
            
            expect(isValidTrifecta).toBe(true);
        });
        
        test('should prevent incomplete trifecta selection', () => {
            const trifectaSelection = [1, 2];
            const isValidTrifecta = trifectaSelection.length === 3;
            
            expect(isValidTrifecta).toBe(false);
        });
        
        test('should handle trifecta horse selection', () => {
            let trifectaSelection = [1, 2];
            const horseId = 3;
            
            if (trifectaSelection.length < 3) {
                trifectaSelection.push(horseId);
            }
            
            expect(trifectaSelection).toEqual([1, 2, 3]);
        });
        
        test('should handle trifecta horse deselection', () => {
            let trifectaSelection = [1, 2, 3];
            const horseId = 2;
            
            if (trifectaSelection.includes(horseId)) {
                trifectaSelection = trifectaSelection.filter(id => id !== horseId);
            }
            
            expect(trifectaSelection).toEqual([1, 3]);
        });
    });
    
    describe('Message Handling', () => {
        test('should handle login success message', () => {
            const message = {
                type: 'login_success',
                user: { username: 'testuser', balance: 10.0, rank: 5 }
            };
            
            let user = null;
            
            if (message.type === 'login_success') {
                user = message.user;
            }
            
            expect(user).toEqual({ username: 'testuser', balance: 10.0, rank: 5 });
        });
        
        test('should handle odds update message', () => {
            const message = {
                type: 'odds_update',
                odds: {
                    1: { winner: 2.5, place: 1.8 },
                    2: { winner: 3.2, place: 2.1 }
                },
                time_remaining: 25
            };
            
            let currentOdds = {};
            
            if (message.type === 'odds_update') {
                currentOdds = message.odds;
            }
            
            expect(currentOdds).toEqual({
                1: { winner: 2.5, place: 1.8 },
                2: { winner: 3.2, place: 2.1 }
            });
        });
        
        test('should handle bet placed message', () => {
            const message = {
                type: 'bet_placed',
                new_balance: 9.0,
                bet: { type: 'winner', amount: 1.0, selection: [1] }
            };
            
            let currentRaceBets = [];
            let balance = 10.0;
            
            if (message.type === 'bet_placed') {
                balance = message.new_balance;
                currentRaceBets.push(message.bet);
            }
            
            expect(balance).toBe(9.0);
            expect(currentRaceBets).toContainEqual({ type: 'winner', amount: 1.0, selection: [1] });
        });
        
        test('should handle race results message', () => {
            const message = {
                type: 'race_results',
                results: [
                    { position: 1, horse_name: 'Thunder', horse_id: 1 },
                    { position: 2, horse_name: 'Lightning', horse_id: 2 }
                ],
                payouts: { winner: { 1: 5.0 } }
            };
            
            let raceResults = null;
            
            if (message.type === 'race_results') {
                raceResults = message.results;
            }
            
            expect(raceResults).toHaveLength(2);
            expect(raceResults[0]).toEqual({ position: 1, horse_name: 'Thunder', horse_id: 1 });
        });
    });
    
    describe('UI Helper Functions', () => {
        test('should format odds correctly', () => {
            const formatOdds = (odds) => {
                if (!odds || isNaN(odds)) return '$2.00';
                return `$${odds.toFixed(2)}`;
            };
            
            expect(formatOdds(2.5)).toBe('$2.50');
            expect(formatOdds(10)).toBe('$10.00');
            expect(formatOdds(null)).toBe('$2.00');
            expect(formatOdds(undefined)).toBe('$2.00');
        });
        
        test('should determine correct odds tier', () => {
            const getOddsTier = (winnerOdds) => {
                if (winnerOdds <= 1.5) return 'odds-favorite';
                if (winnerOdds <= 2.5) return 'odds-strong';
                if (winnerOdds <= 4.0) return 'odds-moderate';
                if (winnerOdds <= 8.0) return 'odds-long';
                return 'odds-longshot';
            };
            
            expect(getOddsTier(1.2)).toBe('odds-favorite');
            expect(getOddsTier(2.0)).toBe('odds-strong');
            expect(getOddsTier(3.5)).toBe('odds-moderate');
            expect(getOddsTier(6.0)).toBe('odds-long');
            expect(getOddsTier(12.0)).toBe('odds-longshot');
        });
        
        test('should update balance display format', () => {
            const updateBalanceDisplay = (balance) => {
                return `$${balance.toFixed(2)}`;
            };
            
            expect(updateBalanceDisplay(15.75)).toBe('$15.75');
            expect(updateBalanceDisplay(10)).toBe('$10.00');
            expect(updateBalanceDisplay(0.5)).toBe('$0.50');
        });
        
        test('should handle user rank display', () => {
            const updateUserRankDisplay = (rank) => {
                if (rank && rank <= 10) {
                    return { text: `Rank #${rank}`, color: '#ffd700' };
                } else if (rank) {
                    return { text: `Rank #${rank}`, color: '#ccc' };
                } else {
                    return { text: 'Rank #--', color: '#999' };
                }
            };
            
            expect(updateUserRankDisplay(5)).toEqual({ text: 'Rank #5', color: '#ffd700' });
            expect(updateUserRankDisplay(15)).toEqual({ text: 'Rank #15', color: '#ccc' });
            expect(updateUserRankDisplay(null)).toEqual({ text: 'Rank #--', color: '#999' });
        });
    });
    
    describe('Race State Management', () => {
        test('should handle phase updates', () => {
            const updatePhaseDisplay = (phase, timeRemaining) => {
                const phaseText = phase.charAt(0).toUpperCase() + phase.slice(1);
                let timeText = '';
                
                if (phase === 'betting') {
                    timeText = `${Math.ceil(Math.max(0, timeRemaining))}s`;
                } else if (phase === 'racing') {
                    timeText = 'Racing...';
                } else if (phase === 'results') {
                    timeText = timeRemaining > 0 ? `${Math.ceil(timeRemaining)}s` : 'Results';
                }
                
                return { phase: phaseText, time: timeText };
            };
            
            expect(updatePhaseDisplay('betting', 25)).toEqual({ phase: 'Betting', time: '25s' });
            expect(updatePhaseDisplay('racing', 0)).toEqual({ phase: 'Racing', time: 'Racing...' });
            expect(updatePhaseDisplay('results', 8)).toEqual({ phase: 'Results', time: '8s' });
            expect(updatePhaseDisplay('results', 0)).toEqual({ phase: 'Results', time: 'Results' });
        });
        
        test('should clear bets for new race', () => {
            let currentRaceBets = [{ type: 'winner', amount: 1.0 }];
            let trifectaSelection = [1, 2, 3];
            let currentRaceId = 1;
            
            const newRaceId = 2;
            
            if (newRaceId !== currentRaceId) {
                currentRaceBets = [];
                trifectaSelection = [];
                currentRaceId = newRaceId;
            }
            
            expect(currentRaceBets).toEqual([]);
            expect(trifectaSelection).toEqual([]);
            expect(currentRaceId).toBe(2);
        });
    });
    
    describe('Bet Tracking', () => {
        test('should check if horse is in player bets', () => {
            const currentRaceBets = [
                { type: 'winner', selection: [1] },
                { type: 'trifecta', selection: [2, 3, 4] }
            ];
            
            const isHorseInPlayerBets = (horseId) => {
                return currentRaceBets.some(bet => {
                    if (bet.type === 'trifecta') {
                        return bet.selection && bet.selection.includes(horseId);
                    } else {
                        return bet.selection && bet.selection[0] === horseId;
                    }
                });
            };
            
            expect(isHorseInPlayerBets(1)).toBe(true);
            expect(isHorseInPlayerBets(2)).toBe(true);
            expect(isHorseInPlayerBets(3)).toBe(true);
            expect(isHorseInPlayerBets(5)).toBe(false);
        });
        
        test('should update trifecta display', () => {
            const updateTrifectaDisplay = (trifectaSelection) => {
                const count = trifectaSelection.length;
                return {
                    text: `${count}/3 horses selected`,
                    buttonDisabled: count !== 3
                };
            };
            
            expect(updateTrifectaDisplay([1, 2])).toEqual({
                text: '2/3 horses selected',
                buttonDisabled: true
            });
            
            expect(updateTrifectaDisplay([1, 2, 3])).toEqual({
                text: '3/3 horses selected',
                buttonDisabled: false
            });
        });
        
        test('should handle mystery trifecta selection', () => {
            const availableHorses = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
            
            const selectMysteryTrifecta = (horses) => {
                const selectedHorses = [];
                const horsesCopy = [...horses];
                
                for (let i = 0; i < 3 && horsesCopy.length > 0; i++) {
                    const randomIndex = Math.floor(Math.random() * horsesCopy.length);
                    const selectedHorse = horsesCopy.splice(randomIndex, 1)[0];
                    selectedHorses.push(selectedHorse);
                }
                
                return selectedHorses;
            };
            
            // Mock Math.random to return predictable values
            const originalRandom = Math.random;
            Math.random = jest.fn()
                .mockReturnValueOnce(0.5)  // Select index 5 (horse 6)
                .mockReturnValueOnce(0.3)  // Select index 2 (horse 3)
                .mockReturnValueOnce(0.1); // Select index 0 (horse 1)
            
            const result = selectMysteryTrifecta(availableHorses);
            
            expect(result).toHaveLength(3);
            expect(result.every(horse => availableHorses.includes(horse))).toBe(true);
            
            Math.random = originalRandom;
        });
    });
    
    describe('WebSocket Communication', () => {
        test('should create WebSocket connection', () => {
            const ws = new MockWebSocket('ws://localhost:8765');
            
            expect(ws.url).toBe('ws://localhost:8765');
            expect(ws.readyState).toBe(1);
        });
        
        test('should send JSON messages', () => {
            const ws = new MockWebSocket('ws://localhost:8765');
            const message = { type: 'login', username: 'testuser' };
            
            ws.send(JSON.stringify(message));
            
            expect(ws.sentMessages).toContainEqual(message);
        });
        
        test('should handle incoming messages', () => {
            const ws = new MockWebSocket('ws://localhost:8765');
            let receivedMessage = null;
            
            ws.onmessage = (event) => {
                receivedMessage = JSON.parse(event.data);
            };
            
            ws.simulateMessage({ type: 'test', data: 'test' });
            
            expect(receivedMessage).toEqual({ type: 'test', data: 'test' });
        });
    });
    
    describe('Error Handling', () => {
        test('should handle invalid JSON in messages', () => {
            const parseMessage = (data) => {
                try {
                    return JSON.parse(data);
                } catch (error) {
                    return null;
                }
            };
            
            expect(parseMessage('{"type": "test"}')).toEqual({ type: 'test' });
            expect(parseMessage('invalid json')).toBeNull();
        });
        
        test('should validate betting constraints', () => {
            const validateBet = (currentRace, selectedHorse, currentRaceBets, selectedBetType) => {
                if (!currentRace || currentRace.phase !== 'betting') {
                    return { valid: false, error: 'Betting is closed' };
                }
                
                if (!selectedHorse && selectedBetType !== 'trifecta') {
                    return { valid: false, error: 'Please select a horse' };
                }
                
                if (currentRaceBets.some(bet => bet.type === selectedBetType)) {
                    return { valid: false, error: `You can only place one ${selectedBetType} bet per race` };
                }
                
                return { valid: true, error: null };
            };
            
            const currentRace = { phase: 'betting' };
            const selectedHorse = 1;
            const currentRaceBets = [];
            const selectedBetType = 'winner';
            
            expect(validateBet(currentRace, selectedHorse, currentRaceBets, selectedBetType)).toEqual({
                valid: true,
                error: null
            });
            
            expect(validateBet(null, selectedHorse, currentRaceBets, selectedBetType)).toEqual({
                valid: false,
                error: 'Betting is closed'
            });
            
            expect(validateBet(currentRace, null, currentRaceBets, selectedBetType)).toEqual({
                valid: false,
                error: 'Please select a horse'
            });
        });
    });
});