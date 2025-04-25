package main

import (
	"fmt"
	"net/http"
)

func helloHandler(w http.ResponseWriter, r *http.Request) {
	name := r.URL.Query().Get("name")
	fmt.Fprintf(w, "Hello im printing the name that has been fetched from the url query paramenter %s!", name)
}
func main() {
	http.HandleFunc("/hello", helloHandler)
	http.ListenAndServe(":12000", nil)
}
