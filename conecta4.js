const readline = require("readline");

const ROWS = 6;
const COLS = 7;
let board = Array.from({ length: ROWS }, () => Array(COLS).fill(0));
let currentPlayer = 1;
let playing = true;

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function printBoard() {
  console.clear();
  console.log("Conecta 4 (Jug1 = 🔴, Jug2 = 🟡)\n");
  for (let r = 0; r < ROWS; r++) {
    let rowStr = "";
    for (let c = 0; c < COLS; c++) {
      if (board[r][c] === 0) rowStr += "[ ]";
      if (board[r][c] === 1) rowStr += "[🔴]";
      if (board[r][c] === 2) rowStr += "[🟡]";
    }
    console.log(rowStr);
  }
  console.log("  1  2  3  4  5  6  7");
}

function askMove() {
  if (!playing) {
    rl.close();
    return;
  }
  rl.question(`Turno Jugador ${currentPlayer} (${currentPlayer === 1 ? "🔴" : "🟡"}) - Elige columna (1-7): `, (input) => {
    const col = parseInt(input) - 1;
    if (isNaN(col) || col < 0 || col >= COLS) {
      console.log("Columna inválida.");
      return askMove();
    }
    for (let r = ROWS - 1; r >= 0; r--) {
      if (board[r][col] === 0) {
        board[r][col] = currentPlayer;
        printBoard();
        if (checkWin(r, col, currentPlayer)) {
          console.log(`¡Jugador ${currentPlayer} gana!`);
          playing = false;
          return askMove();
        } else if (isBoardFull()) {
          console.log("¡Empate, tablero lleno!");
          playing = false;
          return askMove();
        }
        currentPlayer = currentPlayer === 1 ? 2 : 1;
        return askMove();
      }
    }
    console.log("Columna llena, elige otra.");
    askMove();
  });
}

function isBoardFull() {
  return board.every(row => row.every(cell => cell !== 0));
}

function checkWin(row, col, player) {
  const directions = [
    { dr: 0, dc: 1 },
    { dr: 1, dc: 0 },
    { dr: 1, dc: 1 },
    { dr: 1, dc: -1 }
  ];
  for (const { dr, dc } of directions) {
    let count = 1;
    count += countDirection(row, col, dr, dc, player);
    count += countDirection(row, col, -dr, -dc, player);
    if (count >= 4) return true;
  }
  return false;
}

function countDirection(r, c, dr, dc, player) {
  let cnt = 0;
  r += dr;
  c += dc;
  while (r >= 0 && r < ROWS && c >= 0 && c < COLS && board[r][c] === player) {
    cnt++;
    r += dr;
    c += dc;
  }
  return cnt;
}

printBoard();
askMove();
