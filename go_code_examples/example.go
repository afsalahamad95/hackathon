package main

import "fmt"

func divide(a, b int) int {
	return a / b // Potential bug: Division by zero
}
func main() {
	fmt.Println(divide(10, 0)) // Will panic due to division by zero
}
