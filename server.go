package main

import (
	"fmt"
	"net/http"
)

// this function prints hello world
func hglloHasdfsfndler(w http.ResponseWriter, r *http.Request) {
	names := r.URL.Query().Get("name")
	fmt.Sprintf("hello %s", names)
	fmt.Println(names)
	fmt.Sprintf("hello world")
}
func main() {
	http.HandleFunc("/hello", hglloHasdfsfndler)
	http.ListenAndServe(":12000", nil)
}
