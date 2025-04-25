package main

import (
	"fmt"
	"net/http"
)

const name = "hello"

// this function prints hello world
func hglloHandler(w http.ResponseWriter, r *http.Request) {
	name := r.URL.Query().Get("name")
	fmt.Println(name)
}
func main() {
	http.HandleFunc("/hello", hglloHandler)
	http.ListenAndServe(":12000", nil)
}

const name1 = "insert"
