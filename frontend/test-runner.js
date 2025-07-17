#!/usr/bin/env node

/**
 * Test Runner for SaddleUp.io Frontend Tests
 * 
 * This script runs the frontend unit tests and provides detailed reporting
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class TestRunner {
    constructor() {
        this.frontendDir = __dirname;
        this.rootDir = path.join(__dirname, '..');
    }

    async run() {
        console.log('🏇 SaddleUp.io Frontend Test Runner');
        console.log('=====================================\n');

        try {
            // Check if we're in the correct directory
            this.validateEnvironment();
            
            // Install dependencies if needed
            await this.installDependencies();
            
            // Run tests
            await this.runTests();
            
            // Generate coverage report
            await this.generateCoverageReport();
            
            console.log('\n✅ All tests completed successfully!');
            
        } catch (error) {
            console.error('\n❌ Test run failed:', error.message);
            process.exit(1);
        }
    }

    validateEnvironment() {
        console.log('🔍 Validating test environment...');
        
        const requiredFiles = [
            'script.js',
            'script.test.js',
            'package.json',
            'jest.config.js',
            'jest.setup.js'
        ];

        const missingFiles = requiredFiles.filter(file => 
            !fs.existsSync(path.join(this.frontendDir, file))
        );

        if (missingFiles.length > 0) {
            throw new Error(`Missing required files: ${missingFiles.join(', ')}`);
        }

        console.log('✅ Environment validation passed\n');
    }

    async installDependencies() {
        console.log('📦 Installing test dependencies...');
        
        try {
            // Check if node_modules exists
            if (!fs.existsSync(path.join(this.frontendDir, 'node_modules'))) {
                execSync('npm install', { 
                    cwd: this.frontendDir, 
                    stdio: 'inherit' 
                });
            } else {
                console.log('✅ Dependencies already installed');
            }
        } catch (error) {
            throw new Error(`Failed to install dependencies: ${error.message}`);
        }
        
        console.log('');
    }

    async runTests() {
        console.log('🧪 Running frontend unit tests...');
        
        try {
            execSync('npm test', { 
                cwd: this.frontendDir, 
                stdio: 'inherit' 
            });
        } catch (error) {
            throw new Error(`Test execution failed: ${error.message}`);
        }
        
        console.log('');
    }

    async generateCoverageReport() {
        console.log('📊 Generating coverage report...');
        
        try {
            execSync('npm run test:coverage', { 
                cwd: this.frontendDir, 
                stdio: 'inherit' 
            });
            
            const coverageFile = path.join(this.frontendDir, 'coverage', 'lcov-report', 'index.html');
            if (fs.existsSync(coverageFile)) {
                console.log(`📈 Coverage report generated: ${coverageFile}`);
            }
        } catch (error) {
            console.warn(`⚠️  Coverage report generation failed: ${error.message}`);
        }
        
        console.log('');
    }
}

// Run the test runner
if (require.main === module) {
    const runner = new TestRunner();
    runner.run();
}

module.exports = TestRunner;