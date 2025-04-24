package main

import (
	"fmt"
	"net/http"
)

const unnused = 10

func helloHandler(w http.ResponseWriter, r *http.Request) {
	name := r.URL.Query().Get("name")
	fmt.Fprintf(w, "Hello %s!", name)
}
func main() {
	http.HandleFunc("/hello", helloHandler)
	http.ListenAndServe(":12000", nil)
}
