class SaddleUpGame {
    constructor() {
        this.ws = null;
        this.user = null;
        this.currentRace = null;
        this.selectedBetType = 'winner';
        this.selectedHorse = null;
        this.trifectaSelection = [null, null, null];
        
        this.initializeElements();
        this.setupEventListeners();
        this.connect();
    }
    
    initializeElements() {
        // Screens
        this.loginScreen = document.getElementById('login-screen');
        this.gameScreen = document.getElementById('game-screen');
        
        // Login elements
        this.loginForm = document.getElementById('login-form');
        this.usernameInput = document.getElementById('username');
        
        // Game elements
        this.userName = document.getElementById('user-name');
        this.userRank = document.getElementById('user-rank');
        this.userBalance = document.getElementById('user-balance');
        this.raceTitle = document.getElementById('race-title');
        this.racePhase = document.getElementById('race-phase');
        this.timeRemaining = document.getElementById('time-remaining');
        this.trackLanes = document.getElementById('track-lanes');
        this.horsesGrid = document.getElementById('horses-grid');
        this.raceResults = document.getElementById('race-results');
        this.resultsListEl = document.getElementById('results-list');
        this.payoutInfo = document.getElementById('payout-info');
        
        // Betting elements
        this.betTypes = document.querySelectorAll('.bet-type');
        this.singleBet = document.getElementById('single-bet');
        this.trifectaBet = document.getElementById('trifecta-bet');
        this.trifectaSelects = [
            document.getElementById('trifecta-1st'),
            document.getElementById('trifecta-2nd'),
            document.getElementById('trifecta-3rd')
        ];
        this.placeTrifectaBtn = document.getElementById('place-trifecta-btn');
        
        // Leaderboard elements
        this.leaderboardList = document.getElementById('leaderboard-list');
        
        // Error message
        this.errorMessage = document.getElementById('error-message');
        
        // Active bets elements
        this.activeBets = document.getElementById('active-bets');
        this.betsList = document.getElementById('bets-list');
        
        // Track user's bets for current race
        this.currentRaceBets = [];
        
        // Store current odds for potential payout calculations
        this.currentOdds = {};
    }
    
    setupEventListeners() {
        // Login
        this.loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.login();
        });
        
        // Bet type selection
        this.betTypes.forEach(btn => {
            btn.addEventListener('click', () => {
                this.selectBetType(btn.dataset.type);
            });
        });
        
        // Trifecta betting
        this.placeTrifectaBtn.addEventListener('click', () => {
            this.placeTrifectaBet();
        });
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname || 'localhost';
        const port = '8765';
        
        this.ws = new WebSocket(`${protocol}//${host}:${port}`);
        
        this.ws.onopen = () => {
            console.log('Connected to server');
            this.showSuccess('Connected to server');
        };
        
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };
        
        this.ws.onclose = () => {
            console.log('Disconnected from server');
            setTimeout(() => this.connect(), 3000); // Reconnect after 3 seconds
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showError('Connection error. Trying to reconnect...');
        };
    }
    
    handleMessage(message) {
        // Update user object if included in any message
        if (message.user) {
            this.updateUser(message.user);
        }
        
        switch (message.type) {
            case 'connection_established':
                console.log('Connection established');
                break;
                
            case 'login_success':
                this.user = message.user;
                this.showGameScreen();
                break;
                
            case 'race_state':
                this.updateRaceState(message.race);
                break;
                
            case 'odds_update':
                this.updateOdds(message.odds, message.time_remaining);
                break;
                
            case 'phase_update':
                this.updatePhase(message.phase, message.time_remaining);
                break;
                
            case 'race_update':
                this.updateHorsePositions(message.horses);
                break;
                
            case 'race_results':
                this.showRaceResults(message.results, message.payouts, message.trifecta_info, message.top_winners);
                break;
                
            case 'bet_placed':
                this.updateBalance(message.new_balance);
                this.addBetToCurrentRace(message.bet);
                this.showSuccess('Bet placed successfully!');
                break;
                
            case 'leaderboard':
                this.updateLeaderboard(message.leaders, message.current_user_rank);
                break;
                
            case 'error':
                this.showError(message.message);
                break;
        }
    }
    
    login() {
        const username = this.usernameInput.value.trim();
        if (!username) {
            this.showError('Please enter a username');
            return;
        }
        
        this.send({
            type: 'login',
            username: username
        });
    }
    
    showGameScreen() {
        this.loginScreen.classList.remove('active');
        this.gameScreen.classList.add('active');
        
        this.userName.textContent = this.user.username;
        this.updateBalance(this.user.balance);
        this.updateUserRank(this.user.rank);
        
        // Request initial race state and leaderboard
        this.send({ type: 'get_race_state' });
        this.send({ type: 'get_leaderboard' });
    }
    
    updateRaceState(race) {
        // Clear bets for new race - check this BEFORE updating currentRace
        if (!this.currentRace || race.id !== this.currentRace.id) {
            this.currentRaceBets = [];
            this.payoutInfo.innerHTML = '';
        }
        
        this.currentRace = race;
        this.raceTitle.textContent = `Race #${race.id}`;
        this.updatePhase(race.phase, race.time_remaining);
        this.createTrack(race.horses);
        this.updateBettingOptions(race.horses, race.odds);
        
        // Show/hide track and results based on phase
        const raceTrack = document.querySelector('.race-track');
        if (race.phase === 'results') {
            raceTrack.style.display = 'none';
            this.raceResults.classList.remove('hidden');
            this.activeBets.classList.add('hidden');
        } else if (race.phase === 'betting') {
            raceTrack.style.display = 'none';
            this.raceResults.classList.add('hidden');
            this.activeBets.classList.add('hidden');
        } else {
            raceTrack.style.display = 'block';
            this.raceResults.classList.add('hidden');
            
            // Show active bets during racing phase if user has bets
            if (race.phase === 'racing' && this.currentRaceBets.length > 0) {
                this.activeBets.classList.remove('hidden');
                this.updateActiveBetsDisplay();
            } else {
                this.activeBets.classList.add('hidden');
            }
        }
    }
    
    updatePhase(phase, timeRemaining) {
        this.racePhase.textContent = phase.charAt(0).toUpperCase() + phase.slice(1);
        
        // Handle time display based on phase
        if (phase === 'betting') {
            this.timeRemaining.textContent = `${Math.ceil(Math.max(0, timeRemaining))}s`;
        } else if (phase === 'racing') {
            this.timeRemaining.textContent = 'Racing...';
        } else if (phase === 'results') {
            if (timeRemaining > 0) {
                this.timeRemaining.textContent = `${Math.ceil(timeRemaining)}s`;
            } else {
                this.timeRemaining.textContent = 'Results';
            }
        } else {
            this.timeRemaining.textContent = '';
        }
        
        // Update phase styling
        this.racePhase.className = `phase-${phase}`;
        
        // Show/hide betting panel based on phase
        const bettingPanel = document.querySelector('.betting-panel');
        if (phase === 'betting') {
            bettingPanel.style.display = 'block';
        } else {
            bettingPanel.style.display = 'none';
        }
    }
    
    createTrack(horses) {
        this.trackLanes.innerHTML = '';
        
        horses.forEach(horse => {
            const lane = document.createElement('div');
            lane.className = 'horse-lane';
            
            // Get horse odds for color coding (use current odds if available, otherwise default)
            let oddsTier = 'odds-moderate'; // default
            if (this.currentOdds && this.currentOdds[horse.id] && this.currentOdds[horse.id].winner) {
                oddsTier = this.getOddsTier(this.currentOdds[horse.id].winner);
            }
            
            lane.innerHTML = `
                <div class="horse ${oddsTier}" id="horse-${horse.id}" style="left: ${horse.position}%">
                    ${horse.id}
                </div>
                <div class="horse-info">
                    ${horse.name}
                </div>
            `;
            this.trackLanes.appendChild(lane);
        });
    }
    
    updateHorsePositions(horses) {
        horses.forEach(horse => {
            const horseEl = document.getElementById(`horse-${horse.id}`);
            if (horseEl) {
                horseEl.style.left = `${Math.min(horse.position, 95)}%`;
                
                if (horse.finished) {
                    horseEl.style.background = '#ffd700';
                }
            }
        });
    }
    
    updateBettingOptions(horses, odds) {
        // Update single bet options (winner/place)
        this.horsesGrid.innerHTML = '';
        horses.forEach(horse => {
            const btn = document.createElement('button');
            btn.dataset.horseId = horse.id;
            
            const winnerOdds = odds[horse.id]?.winner || 2.0;
            const placeOdds = odds[horse.id]?.place || 1.5;
            
            // Apply base class and odds-based color class
            const oddsTier = this.getOddsTier(winnerOdds);
            btn.className = `horse-bet-btn ${oddsTier}`;
            
            btn.innerHTML = `
                <div class="horse-name">${horse.name}</div>
                <div class="odds">
                    Win: ${this.formatOdds(winnerOdds)}<br>
                    Place: ${this.formatOdds(placeOdds)}
                </div>
            `;
            
            btn.addEventListener('click', () => {
                this.selectHorse(horse.id, btn);
            });
            
            this.horsesGrid.appendChild(btn);
        });
        
        // Update trifecta selects
        this.trifectaSelects.forEach(select => {
            const currentValue = select.value;
            select.innerHTML = '<option value="">Select Horse</option>';
            
            horses.forEach(horse => {
                const option = document.createElement('option');
                option.value = horse.id;
                option.textContent = `#${horse.id} ${horse.name}`;
                select.appendChild(option);
            });
            
            select.value = currentValue;
        });
    }
    
    updateOdds(odds, timeRemaining) {
        this.timeRemaining.textContent = `${Math.ceil(Math.max(0, timeRemaining))}s`;
        
        // Store current odds for potential payout calculations
        this.currentOdds = odds;
        
        // Update odds display in betting buttons
        document.querySelectorAll('.horse-bet-btn').forEach(btn => {
            const horseId = parseInt(btn.dataset.horseId);
            const oddsEl = btn.querySelector('.odds');
            if (oddsEl && odds[horseId]) {
                const winnerOdds = odds[horseId].winner;
                const placeOdds = odds[horseId].place;
                
                // Update odds text
                oddsEl.innerHTML = `
                    Win: ${this.formatOdds(winnerOdds)}<br>
                    Place: ${this.formatOdds(placeOdds)}
                `;
                
                // Update color class based on new odds
                const newOddsTier = this.getOddsTier(winnerOdds);
                btn.className = btn.className.replace(/odds-\w+/g, '').trim();
                btn.className += ` ${newOddsTier}`;
            }
        });
        
        // Update racing horse colors based on new odds
        this.updateRacingHorseColors(odds);
        
        // Update active bets display with current odds
        if (this.currentRaceBets.length > 0) {
            this.updateActiveBetsDisplay();
        }
    }
    
    selectBetType(type) {
        this.selectedBetType = type;
        
        // Update active bet type button
        this.betTypes.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.type === type);
        });
        
        // Show appropriate betting section
        this.singleBet.classList.toggle('active', type !== 'trifecta');
        this.trifectaBet.classList.toggle('active', type === 'trifecta');
        
        // Clear selections
        this.selectedHorse = null;
        this.trifectaSelection = [null, null, null];
        this.clearSelections();
    }
    
    selectHorse(horseId, btnElement) {
        if (this.selectedBetType === 'trifecta') return;
        
        this.selectedHorse = horseId;
        
        // Update visual selection
        document.querySelectorAll('.horse-bet-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        btnElement.classList.add('selected');
        
        // Place bet immediately
        this.placeBet();
    }
    
    placeBet() {
        if (!this.currentRace || this.currentRace.phase !== 'betting') {
            this.showError('Betting is closed');
            return;
        }
        
        if (this.selectedBetType === 'trifecta') {
            this.placeTrifectaBet();
            return;
        }
        
        if (!this.selectedHorse) {
            this.showError('Please select a horse');
            return;
        }
        
        // Check if user already has a bet of this type
        if (this.currentRaceBets.some(bet => bet.type === this.selectedBetType)) {
            this.showError(`You can only place one ${this.selectedBetType} bet per race`);
            return;
        }
        
        this.send({
            type: 'place_bet',
            bet_type: this.selectedBetType,
            amount: 1.0,
            selection: [this.selectedHorse]
        });
        
        this.selectedHorse = null;
        this.clearSelections();
    }
    
    placeTrifectaBet() {
        const selection = [
            parseInt(this.trifectaSelects[0].value),
            parseInt(this.trifectaSelects[1].value),
            parseInt(this.trifectaSelects[2].value)
        ];
        
        if (selection.some(val => !val)) {
            this.showError('Please select all three horses');
            return;
        }
        
        if (new Set(selection).size !== 3) {
            this.showError('Please select three different horses');
            return;
        }
        
        // Check if user already has a trifecta bet
        if (this.currentRaceBets.some(bet => bet.type === 'trifecta')) {
            this.showError('You can only place one trifecta bet per race');
            return;
        }
        
        this.send({
            type: 'place_bet',
            bet_type: 'trifecta',
            amount: 1.0,
            selection: selection
        });
        
        // Clear trifecta selection
        this.trifectaSelects.forEach(select => select.value = '');
    }
    
    clearSelections() {
        document.querySelectorAll('.horse-bet-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
    }
    
    showRaceResults(results, payouts, trifectaInfo, topWinners) {
        this.resultsListEl.innerHTML = '';
        
        // Create a comprehensive results layout
        const resultsContainer = document.createElement('div');
        resultsContainer.className = 'results-container';
        
        // Top 3 horses section
        const horsesSection = document.createElement('div');
        horsesSection.className = 'horses-results-section';
        horsesSection.innerHTML = '<h4 style="color: #ffd700; margin-bottom: 1rem;">🏁 Race Finish</h4>';
        
        results.forEach(result => {
            const resultEl = document.createElement('div');
            resultEl.className = 'result-item';
            
            let positionIcon = '';
            if (result.position === 1) positionIcon = '🥇';
            else if (result.position === 2) positionIcon = '🥈';
            else if (result.position === 3) positionIcon = '🥉';
            
            resultEl.innerHTML = `
                <div>
                    <span>${positionIcon} ${result.position}. ${result.horse_name} (#${result.horse_id})</span>
                </div>
                <div style="font-size: 0.9rem; color: #ccc;">
                    Win: ${this.formatOdds(result.winner_odds)} | Place: ${this.formatOdds(result.place_odds)}
                </div>
            `;
            horsesSection.appendChild(resultEl);
        });
        
        // Trifecta section
        if (trifectaInfo && trifectaInfo.total_pool > 0) {
            const trifectaSection = document.createElement('div');
            trifectaSection.className = 'trifecta-section';
            trifectaSection.innerHTML = `
                <h4 style="color: #ffd700; margin: 1.5rem 0 1rem 0;">🎯 Trifecta Results</h4>
                <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px;">
                    <div>Winning Order: ${trifectaInfo.winning_combination.join('-')}</div>
                    <div>Total Pool: $${trifectaInfo.total_pool.toFixed(2)}</div>
                    <div>Winners: ${trifectaInfo.winners_count}</div>
                    ${trifectaInfo.payout_per_dollar > 0 ? 
                        `<div style="color: #ffd700;">Payout: $${trifectaInfo.payout_per_dollar.toFixed(2)} per $1 bet</div>` : 
                        '<div style="color: #999;">No winning tickets</div>'
                    }
                </div>
            `;
            resultsContainer.appendChild(trifectaSection);
        }
        
        // Top winners section
        if (topWinners && topWinners.length > 0) {
            const winnersSection = document.createElement('div');
            winnersSection.className = 'winners-section';
            winnersSection.innerHTML = '<h4 style="color: #ffd700; margin: 1.5rem 0 1rem 0;">💰 Top Race Winners</h4>';
            
            topWinners.forEach((winner, index) => {
                const winnerEl = document.createElement('div');
                winnerEl.className = 'winner-item';
                
                // Create bets summary
                let betsHtml = '';
                winner.bets.forEach(bet => {
                    if (bet.type === 'trifecta') {
                        betsHtml += `<div class="bet-detail">Trifecta: ${bet.horse_names.join('-')} ($${bet.amount.toFixed(2)})</div>`;
                    } else {
                        betsHtml += `<div class="bet-detail">${bet.type.charAt(0).toUpperCase() + bet.type.slice(1)}: ${bet.horse_name} ($${bet.amount.toFixed(2)})</div>`;
                    }
                });
                
                winnerEl.innerHTML = `
                    <div class="winner-header">
                        <span class="winner-rank">${index + 1}.</span>
                        <span class="winner-name">${winner.username}</span>
                        <span class="winner-amount">+$${winner.total_winnings.toFixed(2)}</span>
                    </div>
                    <div class="winner-bets">
                        ${betsHtml}
                    </div>
                `;
                winnersSection.appendChild(winnerEl);
            });
            
            resultsContainer.appendChild(winnersSection);
        }
        
        // Personal payout section
        const personalSection = document.createElement('div');
        personalSection.className = 'personal-results-section';
        
        let payoutText = '';
        let totalPayout = 0;
        
        if (this.user) {
            ['winner', 'place', 'trifecta'].forEach(type => {
                if (payouts[type] && payouts[type][this.user.id]) {
                    const amount = payouts[type][this.user.id];
                    totalPayout += amount;
                    payoutText += `${type.charAt(0).toUpperCase() + type.slice(1)}: $${amount.toFixed(2)}<br>`;
                }
            });
        }
        
        if (totalPayout > 0) {
            personalSection.innerHTML = `
                <h4 style="color: #ffd700; margin: 1.5rem 0 1rem 0;">🎉 Your Results</h4>
                <div style="background: rgba(255, 215, 0, 0.1); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255, 215, 0, 0.3);">
                    ${payoutText}
                    <div style="font-size: 1.2em; margin-top: 0.5rem; color: #ffd700; font-weight: bold;">
                        Total Winnings: $${totalPayout.toFixed(2)}
                    </div>
                </div>
            `;
        } else {
            personalSection.innerHTML = `
                <h4 style="color: #ffd700; margin: 1.5rem 0 1rem 0;">Your Results</h4>
                <div style="color: #ccc; font-style: italic; text-align: center; padding: 1rem;">
                    Better luck next race!
                </div>
            `;
        }
        
        resultsContainer.appendChild(horsesSection);
        resultsContainer.appendChild(personalSection);
        
        this.resultsListEl.appendChild(resultsContainer);
        this.payoutInfo.innerHTML = ''; // Clear since we're showing it in the results
        
        // Hide race track and show results
        const raceTrack = document.querySelector('.race-track');
        raceTrack.style.display = 'none';
        this.raceResults.classList.remove('hidden');
    }
    
    updateBalance(balance) {
        this.userBalance.textContent = `$${balance.toFixed(2)}`;
        if (this.user) {
            this.user.balance = balance;
        }
    }
    
    updateLeaderboard(leaders, currentUserRank) {
        this.leaderboardList.innerHTML = '';
        
        let userFoundInLeaderboard = false;
        
        leaders.forEach((leader, index) => {
            const item = document.createElement('div');
            item.className = 'leaderboard-item';
            item.innerHTML = `
                <span class="leaderboard-rank">${index + 1}</span>
                <span class="leaderboard-name">${leader.username}</span>
                <span class="leaderboard-balance">$${leader.balance.toFixed(2)}</span>
            `;
            this.leaderboardList.appendChild(item);
            
            // Update user rank if this is the current user
            if (this.user && leader.username === this.user.username) {
                const userRank = leader.rank || index + 1;
                this.user.rank = userRank;  // Store rank in user object
                this.updateUserRank(userRank);
                userFoundInLeaderboard = true;
            }
        });
        
        // If user is not in top 10, use the current_user_rank from backend or stored rank
        if (this.user && !userFoundInLeaderboard) {
            const rankToUse = currentUserRank || this.user.rank;
            if (rankToUse) {
                this.user.rank = rankToUse;  // Store rank in user object
                this.updateUserRank(rankToUse);
            } else {
                this.updateUserRank(null);  // This will show "Rank #--"
            }
        }
    }
    
    updateUser(userData) {
        if (this.user) {
            // Update existing user object
            this.user = { ...this.user, ...userData };
            
            // Update UI elements
            this.userName.textContent = this.user.username;
            this.updateBalance(this.user.balance);
            this.updateUserRank(this.user.rank);
        }
    }
    
    updateUserRank(rank) {
        if (rank && rank <= 10) {
            this.userRank.textContent = `Rank #${rank}`;
            this.userRank.style.color = '#ffd700';
        } else if (rank) {
            this.userRank.textContent = `Rank #${rank}`;
            this.userRank.style.color = '#ccc';
        } else {
            this.userRank.textContent = 'Rank #--';
            this.userRank.style.color = '#999';
        }
    }
    
    formatOdds(odds) {
        if (!odds || isNaN(odds)) return '$2.00';
        
        // Convert odds to dollar payout format (always show 2 decimal places)
        return `$${odds.toFixed(2)}`;
    }
    
    getOddsTier(winnerOdds) {
        // Determine color tier based on winner odds
        if (winnerOdds <= 1.5) return 'odds-favorite';      // Green - Strong favorites
        if (winnerOdds <= 2.5) return 'odds-strong';        // Light green - Good favorites  
        if (winnerOdds <= 4.0) return 'odds-moderate';      // Yellow - Moderate odds
        if (winnerOdds <= 8.0) return 'odds-long';          // Orange - Long odds
        return 'odds-longshot';                              // Red - Longshots
    }
    
    updateRacingHorseColors(odds) {
        // Update the racing horse colors based on current odds
        Object.keys(odds).forEach(horseId => {
            const horseEl = document.getElementById(`horse-${horseId}`);
            if (horseEl && odds[horseId].winner) {
                const newOddsTier = this.getOddsTier(odds[horseId].winner);
                horseEl.className = horseEl.className.replace(/odds-\w+/g, '').trim();
                horseEl.className += ` ${newOddsTier}`;
            }
        });
    }
    
    addBetToCurrentRace(bet) {
        // Add bet info with horse name and odds at time of betting
        const betInfo = { ...bet };
        
        if (bet.type === 'trifecta') {
            // For trifecta, store just the selection numbers
            betInfo.displayText = bet.selection.join('-');
            betInfo.oddsAtBetting = 'Variable';
        } else {
            // For winner/place, get horse name and current odds
            const horse = this.currentRace?.horses.find(h => h.id === bet.selection[0]);
            if (horse) {
                betInfo.displayText = horse.name; // Just the horse name
                betInfo.horseName = horse.name;
                
                // Store odds at time of betting
                const currentOdds = this.getHorseCurrentOdds(horse.id, bet.type);
                betInfo.oddsAtBetting = currentOdds;
            }
        }
        
        this.currentRaceBets.push(betInfo);
    }
    
    updateActiveBetsDisplay() {
        this.betsList.innerHTML = '';
        
        if (this.currentRaceBets.length === 0) {
            this.betsList.innerHTML = '<p style="color: #ccc; text-align: center;">No bets placed this race</p>';
            return;
        }
        
        this.currentRaceBets.forEach(bet => {
            const betEl = document.createElement('div');
            betEl.className = 'bet-item';
            
            // Calculate potential payout based on current odds
            let potentialPayout = 'TBD';
            if (this.currentRace && bet.type !== 'trifecta') {
                const horse = this.currentRace.horses.find(h => h.id === bet.selection[0]);
                if (horse) {
                    const currentOdds = this.getHorseCurrentOdds(horse.id, bet.type);
                    if (currentOdds) {
                        potentialPayout = `$${(bet.amount * currentOdds).toFixed(2)}`;
                    }
                }
            }
            
            betEl.innerHTML = `
                <div class="bet-info">
                    <div class="bet-type">${bet.type}</div>
                    <div class="bet-selection">${bet.displayText}</div>
                    <div class="bet-potential">
                        ${bet.oddsAtBetting !== 'Variable' ? `Odds: ${this.formatOdds(bet.oddsAtBetting)} | ` : ''}Potential: ${potentialPayout}
                    </div>
                </div>
                <div class="bet-amount">$${bet.amount.toFixed(2)}</div>
            `;
            
            this.betsList.appendChild(betEl);
        });
    }
    
    getHorseCurrentOdds(horseId, betType) {
        if (this.currentOdds && this.currentOdds[horseId]) {
            if (betType === 'winner') {
                return this.currentOdds[horseId].winner;
            } else if (betType === 'place') {
                return this.currentOdds[horseId].place;
            }
        }
        return 2.0; // fallback
    }
    
    showError(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.classList.remove('hidden');
        setTimeout(() => {
            this.errorMessage.classList.add('hidden');
        }, 3000);
    }
    
    showSuccess(message) {
        // Create temporary success message
        const successEl = document.createElement('div');
        successEl.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #27ae60;
            color: white;
            padding: 1rem 2rem;
            border-radius: 8px;
            z-index: 1001;
        `;
        successEl.textContent = message;
        document.body.appendChild(successEl);
        
        setTimeout(() => {
            document.body.removeChild(successEl);
        }, 2000);
    }
    
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.error('WebSocket not connected. Current state:', this.ws?.readyState);
            this.showError('Connection not ready. Please wait and try again.');
        }
    }
}

// Initialize the game when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new SaddleUpGame();
});