package main

import (
	"fmt"
	"net/http"
)

func helloHandler(w http.ResponseWriter, r *http.Request) {
	name := r.URL.Query().Get("name")
	fmt.Fprintf(w, "Hello %s!", name)
	fmt.Println("so this ifdjfdfdkfjkdfkdfkdfjvnjajejfkndkfkljferjierjtrgkso this ifdjfdfdkfjkdfkdfkdfjvnjajejfkndkfkljferjierjtrgk")
}
func main() {
	http.HandleFunc("/hello", helloHandler)
	http.ListenAndServe(":12000", nil)
}
