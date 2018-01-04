function plotbardata( json ) {
    var results,
        size = [],
        name = [],
        tag = [],
        chart,
        bars,
        margin = 100,
        x, y,
        xAxis, yAxis
        width = 2500,
        height = 0;

    results = d3.map( json );
    results.each( function(val) {
        size.push( parseInt( val.size, 10 ) );
        name.push( val.name )
        tag.push( val.name + ' ( '+parseInt( val.size, 10 )+' )' )
    } );
    
    height = 30 * size.length;
    
    var title = d3.select("body")
       .append("div")
       .attr("height", 500)
       .attr("transform", "translate(" + 0 + "," + 300 + ")")
       .append("text")
       .attr("dx",0) // padding-right
       .attr("dy", ".35em") // vertical-align: middle
       .style("font-size", "30px")
       .style("font-color", "black")
       .text("Peak Memory Usage/Object")
       
    
    var chart = d3.select("body")
       .append("div")
       .append("svg:svg")
       .attr("class", "chart")
       .attr("margin", 100 )
       .attr("width", width )
       .attr("height", height )
       .attr("transform", "translate(" + 0 + "," + 20 + ")");
    
    var x = d3.scaleLinear()
      .domain([0, d3.max(size)])
      .range([0, 1100]);
      
    var y = d3.scaleLinear()
      .domain([0, d3.max(size)*40])
      .range([0, 300]);  
       
    chart.selectAll("rect")
      .data(size)
     .enter().append("svg:rect")
      .attr("x", 0) 
      .attr("y", function(d,i) { return i*30;})
      .attr("width", x)
      .attr("height", 20);
      
    chart.selectAll("text")
      .data(tag)
     .enter().append("svg:text")
      .attr("x", function(d,i) { return x(size[i]); })
      .attr("y", function(d,i) { return i*30 + 10; })
      .attr("dx",10) // padding-right
      .attr("dy", ".35em") // vertical-align: middle
      .attr("text-anchor", "begin") // text-align: right
      .style("fill", "black") // text-align: right
      .style("font-size", "14px")
      .text(String); 
      
    chart.select(".axis")
      .call(d3.axisBottom(x));
      
    chart.select(".axis")
      .call(d3.axisLeft(y));  
}

plotbardata( mbed_map_peak["children"] )

