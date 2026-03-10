//                                           [2026-03-03 13:45]
//                                          Productivity: Active
#!/usr/bin/env node

/**
 * Thirsty-lang Interactive Training Program
 * Learn Thirsty-lang through interactive lessons at all levels!
 */

const readline = require('readline');
const { ThirstyInterpreter } = require('./index');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// Training levels and lessons
const TRAINING_LEVELS = {
  base: {
    name: '💧 Base Thirsty-lang',
    description: 'Learn the fundamentals',
    lessons: [
      {
        title: 'Lesson 1: Your First Variable',
        instruction: 'Variables store data. Use "drink" to create a variable.\nTry typing: drink water = "H2O"',
        hint: 'Remember: drink variableName = value',
        expectedPattern: /drink\s+\w+\s*=\s*.+/,
        validation: (code, interpreter) => {
          return Object.keys(interpreter.variables).length > 0;
        }
      },
      {
        title: 'Lesson 2: Outputting Values',
        instruction: 'Use "pour" to display values.\nFirst, create a variable with: drink message = "Hello"\nThen display it with: pour message',
        hint: 'Type both lines (you can separate with semicolons or press Enter twice)',
        expectedPattern: /drink.*pour/s,
        validation: (code, interpreter) => {
          return code.includes('drink') && code.includes('pour');
        }
      },
      {
        title: 'Lesson 3: Numbers',
        instruction: 'You can store numbers too!\nTry: drink glasses = 8\npour glasses',
        hint: 'Numbers don\'t need quotes',
        expectedPattern: /drink\s+\w+\s*=\s*\d+/,
        validation: (code, interpreter) => {
          return Object.values(interpreter.variables).some(v => typeof v === 'number');
        }
      }
    ]
  },
  plus: {
    name: '💧+ Thirsty Plus',
    description: 'Add control flow and logic',
    lessons: [
      {
        title: 'Lesson 1: Conditional Statements',
        instruction: 'Use "thirsty" for if statements (coming soon!).\nExample: thirsty temperature > 30\n  pour "Drink more water!"',
        hint: 'This feature will be available in the full Thirsty+ release',
        expectedPattern: /.*/,
        validation: () => true
      }
    ]
  },
  plusplus: {
    name: '💧++ Thirsty Plus Plus',
    description: 'Master functions and loops',
    lessons: [
      {
        title: 'Lesson 1: Functions',
        instruction: 'Use "glass" to define functions (coming soon!).\nExample: glass hydrate(amount)\n  pour amount',
        hint: 'This feature will be available in the full Thirsty++ release',
        expectedPattern: /.*/,
        validation: () => true
      }
    ]
  },
  gods: {
    name: '⚡ ThirstOfGods',
    description: 'Achieve ultimate mastery',
    lessons: [
      {
        title: 'Lesson 1: Classes and OOP',
        instruction: 'Use "fountain" to create classes (coming soon!).\nExample: fountain WaterBottle',
        hint: 'This feature will be available in the full ThirstOfGods release',
        expectedPattern: /.*/,
        validation: () => true
      }
    ]
  }
};

class TrainingProgram {
  constructor() {
    this.currentLevel = null;
    this.currentLessonIndex = 0;
    this.completedLessons = {
      base: [],
      plus: [],
      plusplus: [],
      gods: []
    };
  }

  async start() {
    this.showWelcome();
    await this.showMainMenu();
  }

  showWelcome() {
    console.clear();
    console.log('╔════════════════════════════════════════════════════════════╗');
    console.log('║        🌊 THIRSTY-LANG INTERACTIVE TRAINING 🌊            ║');
    console.log('║                                                            ║');
    console.log('║        Learn to code while staying hydrated!               ║');
    console.log('╚════════════════════════════════════════════════════════════╝');
    console.log('\n');
  }

  async showMainMenu() {
    console.log('\n📚 Select Your Training Level:\n');
    console.log('  1. 💧 Base Thirsty-lang (Beginner)');
    console.log('  2. 💧+ Thirsty Plus (Intermediate)');
    console.log('  3. 💧++ Thirsty Plus Plus (Advanced)');
    console.log('  4. ⚡ ThirstOfGods (Master)');
    console.log('  5. 📊 View Progress');
    console.log('  6. ❌ Exit\n');

    return new Promise((resolve) => {
      rl.question('Enter your choice (1-6): ', async (answer) => {
        switch(answer.trim()) {
          case '1':
            await this.startLevel('base');
            break;
          case '2':
            await this.startLevel('plus');
            break;
          case '3':
            await this.startLevel('plusplus');
            break;
          case '4':
            await this.startLevel('gods');
            break;
          case '5':
            this.showProgress();
            await this.showMainMenu();
            break;
          case '6':
            console.log('\n💧 Stay hydrated and keep learning! Goodbye!\n');
            rl.close();
            resolve();
            return;
          default:
            console.log('Invalid choice. Please try again.');
            await this.showMainMenu();
        }
        resolve();
      });
    });
  }

  async startLevel(levelKey) {
    this.currentLevel = levelKey;
    this.currentLessonIndex = 0;
    const level = TRAINING_LEVELS[levelKey];
    
    console.clear();
    console.log(`\n🎓 ${level.name}`);
    console.log(`📖 ${level.description}\n`);
    console.log('━'.repeat(60));
    
    await this.runLesson();
  }

  async runLesson() {
    const level = TRAINING_LEVELS[this.currentLevel];
    const lesson = level.lessons[this.currentLessonIndex];
    
    if (!lesson) {
      console.log('\n🎉 Congratulations! You\'ve completed all lessons in this level!');
      console.log('💪 Your thirst for knowledge has been quenched!\n');
      await this.waitForEnter();
      await this.showMainMenu();
      return;
    }

    console.log(`\n📝 ${lesson.title}`);
    console.log('─'.repeat(60));
    console.log(lesson.instruction);
    console.log('\n💡 Hint: ' + lesson.hint);
    console.log('\nType your code below (type "skip" to skip, "hint" for help, "menu" to return):');
    
    await this.getLessonInput(lesson);
  }

  async getLessonInput(lesson) {
    return new Promise((resolve) => {
      rl.question('\n> ', async (answer) => {
        const input = answer.trim();
        
        if (input.toLowerCase() === 'menu') {
          await this.showMainMenu();
          resolve();
          return;
        }
        
        if (input.toLowerCase() === 'skip') {
          console.log('⏭️  Lesson skipped.');
          this.currentLessonIndex++;
          await this.runLesson();
          resolve();
          return;
        }
        
        if (input.toLowerCase() === 'hint') {
          console.log('💡 ' + lesson.hint);
          await this.getLessonInput(lesson);
          resolve();
          return;
        }

        // Try to execute the code
        try {
          const interpreter = new ThirstyInterpreter();
          interpreter.execute(input);
          
          if (lesson.validation(input, interpreter)) {
            console.log('\n✅ Excellent! Lesson completed!');
            this.completedLessons[this.currentLevel].push(this.currentLessonIndex);
            
            await this.waitForEnter();
            this.currentLessonIndex++;
            await this.runLesson();
          } else {
            console.log('\n❌ Not quite right. Try again!');
            console.log('💡 Hint: ' + lesson.hint);
            await this.getLessonInput(lesson);
          }
        } catch (error) {
          console.log('\n❌ Error: ' + error.message);
          console.log('Try again or type "hint" for help.');
          await this.getLessonInput(lesson);
        }
        
        resolve();
      });
    });
  }

  showProgress() {
    console.clear();
    console.log('\n📊 Your Training Progress\n');
    console.log('═'.repeat(60));
    
    for (const [key, level] of Object.entries(TRAINING_LEVELS)) {
      const completed = this.completedLessons[key].length;
      const total = level.lessons.length;
      const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
      const bar = '█'.repeat(Math.floor(percentage / 5)) + '░'.repeat(20 - Math.floor(percentage / 5));
      
      console.log(`\n${level.name}`);
      console.log(`[${bar}] ${percentage}% (${completed}/${total} lessons)`);
    }
    
    console.log('\n═'.repeat(60));
  }

  async waitForEnter() {
    return new Promise((resolve) => {
      rl.question('\nPress Enter to continue...', () => {
        resolve();
      });
    });
  }
}

async function main() {
  const program = new TrainingProgram();
  await program.start();
}

if (require.main === module) {
  main();
}

module.exports = TrainingProgram;
