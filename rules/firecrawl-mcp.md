FirecrawlMCP {
  AppliesWhen { about to call any mcp__firecrawl__* tool }

  constraint PickTheToolByBoundary {
    tool = match (the need), taking the first arm that matches {
      case (a library, API, or error question) => firecrawl_developer_search
      case (a page whose URL you hold) => firecrawl_scrape
      case (a page you must find) => firecrawl_search
      case (a site's URLs) => firecrawl_map
      case (many pages of one site) => firecrawl_crawl
      case (content behind a click, form, or login) => firecrawl_interact
      case (a recurring watch) => firecrawl_monitor_create
    }
    (a search names the page that answers) => scrape it, since a snippet
      carries an excerpt rather than the page
  }

  constraint FreshnessIsAChoice {
    scrape returns a copy up to two days old by default, so pass maxAge: 0
      wherever the answer turns on current state
    require no successful response counts as proof the state still holds
    request only the formats you will read, and keep search limits small
  }

  constraint SessionsCloseAndWritesWait {
    (an interact call would submit, log in, post, or buy) => show the exact
      prompt or code and act on the user's approval alone
    call firecrawl_interact_stop as soon as the work ends, since an open
      session bills per browser minute
  }

  constraint MonitorsSpendOnSchedule {
    (creating, updating, running, or deleting a monitor) => show its
      targets, schedule, goal, recipients, and estimated credits, and act on
      the user's approval alone
    write the goal as what fires an alert and the scope it holds to
  }
}
