import java.util.Scanner;

public class gato {
    private static final int SIZE = 3;
    private static char[][] board = new char[SIZE][SIZE];
    private static char currentPlayer = 'X';
    private static Scanner scanner = new Scanner(System.in);

    public static void main(String[] args) {
        boolean jugarDeNuevo = true;

        System.out.println("=== Juego del Gato ===");

        while (jugarDeNuevo) {
            inicializarTablero();
            currentPlayer = 'X';
            boolean juegoTerminado = false;

            imprimirTablero();

            while (!juegoTerminado) {
                System.out.println("Turno de " + currentPlayer + ". Ingresa fila y columna (1-3) separados por espacio:");
                int fila = -1, col = -1;

                if (scanner.hasNextInt()) {
                    fila = scanner.nextInt();
                    if (scanner.hasNextInt()) {
                        col = scanner.nextInt();
                    } else {
                        scanner.nextLine();
                    }
                } else {
                    scanner.nextLine();
                }

                if (!esEntradaValida(fila, col)) {
                    System.out.println("Entrada inválida. Usa dos números entre 1 y 3.");
                    imprimirTablero();
                    continue;
                }

                int r = fila - 1;
                int c = col - 1;

                if (board[r][c] != ' ') {
                    System.out.println("Esa casilla ya está ocupada, tenta de nuevo.");
                    imprimirTablero();
                    continue;
                }

                board[r][c] = currentPlayer;
                imprimirTablero();

                if (hayGanador(currentPlayer)) {
                    System.out.println("¡Jugador " + currentPlayer + " gana!");
                    juegoTerminado = true;
                } else if (esEmpate()) {
                    System.out.println("Empate.");
                    juegoTerminado = true;
                } else {
                    cambiarJugador();
                }
            }

            System.out.print("¿Quieres jugar otra vez? (S/N): ");
            String respuesta = scanner.next().trim().toUpperCase();
            if (!respuesta.equals("S")) {
                jugarDeNuevo = false;
            }
        }

        System.out.println("Fin del juego. ¡Gracias por jugar!");
    }

    private static void inicializarTablero() {
        for (int i = 0; i < SIZE; i++) {
            for (int j = 0; j < SIZE; j++) {
                board[i][j] = ' ';
            }
        }
    }

    private static void imprimirTablero() {
        System.out.println();
        for (int i = 0; i < SIZE; i++) {
            System.out.print(" ");
            for (int j = 0; j < SIZE; j++) {
                System.out.print(board[i][j]);
                if (j < SIZE - 1) System.out.print(" | ");
            }
            System.out.println();
            if (i < SIZE - 1) System.out.println("---+---+---");
        }
        System.out.println();
    }

    private static boolean esEntradaValida(int fila, int col) {
        return fila >= 1 && fila <= SIZE && col >= 1 && col <= SIZE;
    }

    private static void cambiarJugador() {
        currentPlayer = (currentPlayer == 'X') ? 'O' : 'X';
    }

    private static boolean hayGanador(char jugador) {
        // Filas
        for (int i = 0; i < SIZE; i++) {
            if (board[i][0] == jugador && board[i][1] == jugador && board[i][2] == jugador) {
                return true;
            }
        }
        // Columnas
        for (int j = 0; j < SIZE; j++) {
            if (board[0][j] == jugador && board[1][j] == jugador && board[2][j] == jugador) {
                return true;
            }
        }
        // Diagonales
        if (board[0][0] == jugador && board[1][1] == jugador && board[2][2] == jugador) return true;
        if (board[0][2] == jugador && board[1][1] == jugador && board[2][0] == jugador) return true;

        return false;
    }

    private static boolean esEmpate() {
        for (int i = 0; i < SIZE; i++) {
            for (int j = 0; j < SIZE; j++) {
                if (board[i][j] == ' ') return false;
            }
        }
        return true;
    }
}
